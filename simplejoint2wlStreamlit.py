import streamlit as st
from ThreeSpaceAPIStreamlit import ThreeSpaceSensor
from USB_ExampleClassStreamlit import UsbCom
from scipy.spatial.transform import Rotation
from time import sleep

def quat_multiply(l, r):
    t = [0, 0, 0, 0]
    t[3] = l[3]*r[3] - l[0]*r[0] - l[1]*r[1] - l[2]*r[2]
    t[0] = l[3]*r[0] + l[0]*r[3] + l[1]*r[2] - l[2]*r[1]
    t[1] = l[3]*r[1] + l[1]*r[3] + l[2]*r[0] - l[0]*r[2]
    t[2] = l[3]*r[2] + l[2]*r[3] + l[0]*r[1] - l[1]*r[0]
    return t

def inverse_quaternion(quat: list[float]):
    new_quat = quat.copy()
    for i in range(3):
        new_quat[i] *= -1
    return new_quat

if __name__ == "__main__":
    #NOTE: Due to how Euler Angles work, the middle axis in the decomp order will only have a range of -90 to 90,
    #and when it approaches 90 degrees, it may cause the first and last axis to flip sign. For this reason, the two axes
    #cared about most should be first and last
    euler_decomp_order = "yxz"
    
    #The second sensor will be offset on startup to act as if it is in the exact same initial orientation as
    #the reference sensor. Therefore, the axis the euler angles given effect are based around the reference sensors orientation
    #on the joint
    reference_sensor = 0  # logical ID
    second_sensor = 1  # logical ID
    
    # console output options
    print_to_same_line = True
    print_all_decomp = True
    print_in_decomp_order = False  # if False, print in XYZ order
    
    # sensor setup
    DONGLE_COM = None
    dongle_UsbCom = None
    dongle = None
    while not dongle_UsbCom and not dongle:
        try:
            dongle_UsbCom = UsbCom(DONGLE_COM)
            dongle_UsbCom.open()
            dongle_UsbCom.sensor.reset_input_buffer()
            dongle_UsbCom.sensor.reset_output_buffer()
            dongle_UsbCom.sensor.read_all()
            dongle_UsbCom.close()
            dongle = ThreeSpaceSensor(dongle_UsbCom)
        except Exception as e:
            print("Error detected, attempting dongle restart: " + str(type(e)) + " " + str(e) + "\n")
            try:
                dongle_UsbCom.sensor.write(":226\n".encode())
            except:
                pass
            dongle_UsbCom = None
            dongle = None
            sleep(0.5)

    #Ensure clean start
    dongle.tareWithQuaternion(0, 0, 0, 1, logicalID=reference_sensor)
    dongle.tareWithQuaternion(0, 0, 0, 1, logicalID=second_sensor)

    dongle.offsetWithQuaternion(0, 0, 0, 1, logicalID=reference_sensor)
    dongle.offsetWithQuaternion(0, 0, 0, 1, logicalID=second_sensor)

    #The offset ensures the sensors have the same current representation regardless
    #of their current position and orientation
    print("\nPlace in default position\n")
    sleep(2)
    if print_all_decomp and print_to_same_line:
        print("\n"*5)

    #In regards to the difference rotation
    # q2 * difference = q1

    #Need to calibrate it such that the second sensor is considered the same orientation as the 
    #reference sensor regardless of its current orientation relative to the world.
    #sensor2_quat * dif = reference_quat
    #so dif = inverse(sensor2_quat) * reference_quat

    #Obtaining the default difference between the two sensors as an offset
    reference_quat = list(dongle.getUntaredOrientation(logicalID=reference_sensor)[-4:])
    quat2 = list(dongle.getUntaredOrientation(logicalID=second_sensor)[-4:])
    offset = quat_multiply(inverse_quaternion(quat2), reference_quat)

    #Offset the sensor2 by this, so now the tared quat of sensor2 is identical to the untared of the reference and in the same reference space
    dongle.offsetWithQuaternion(*offset, logicalID=second_sensor)
    
    # console options setup
    decomp_and_axis_order = None
    if print_all_decomp:
        if print_in_decomp_order:  # will print in the decomposition order
            decomp_and_axis_order = (("xyz",(0,1,2)), ("yzx",(0,1,2)), ("zxy",(0,1,2)), ("zyx",(0,1,2)), ("xzy",(0,1,2)), ("yxz",(0,1,2)))
        else:  # will print in XYZ
            decomp_and_axis_order = (("xyz",(0,1,2)), ("yzx",(2,0,1)), ("zxy",(1,2,0)), ("zyx",(2,1,0)), ("xzy",(0,2,1)), ("yxz",(1,0,2)))
    else:
        if print_in_decomp_order:  # will print in the decomposition order
            decomp_and_axis_order = ((euler_decomp_order,(0,1,2)),)
        else:
            decomp_and_axis_order = ((euler_decomp_order,(euler_decomp_order.find('x'),euler_decomp_order.find('y'),euler_decomp_order.find('z'))),)

    while True:
        quat1 = list(dongle.getTaredOrientation(logicalID=reference_sensor)[-4:])
        quat2 = list(dongle.getTaredOrientation(logicalID=second_sensor)[-4:])

        diff_quat = quat_multiply(inverse_quaternion(quat2), quat1)

        #Using scipy to simplify things
        difference_rotation = Rotation.from_quat(diff_quat)
        
        print_lines = []
        for decomp, axis_order in decomp_and_axis_order:
            euler_differences = difference_rotation.as_euler(decomp, degrees=True)
            edx = str(euler_differences[axis_order[0]])
            edy = str(euler_differences[axis_order[1]])
            edz = str(euler_differences[axis_order[2]])
            print_str = "Decomp: " + str(decomp) + ", Axis Order: " + decomp[axis_order[0]] + decomp[axis_order[1]] + decomp[axis_order[2]] + ", " +\
                edx + " "*(26-len(edx)) + edy + " "*(26-len(edy)) + edz + " "*(26-len(edz))  # str len 108
            print_lines.append(print_str)

        if print_to_same_line is True:
            if print_all_decomp:
                print('\033[6A' + "\r\n".join(print_lines), flush=True)
            else:
                print('\033[1A' + "\r\n".join(print_lines), flush=True)
        elif print_all_decomp:
            print("\r\n".join(print_lines) + "\n")
        else:
            print("\r\n".join(print_lines))
        sleep(0)