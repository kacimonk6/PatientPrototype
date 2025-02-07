import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import boto3
from io import StringIO, BytesIO
import streamlit as st

from colorama import init, Fore, Style
import streamlit as st
import re
import bcrypt
import sqlite3




# Connect to SQLite database (or create it)
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Create users table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, email TEXT)''')
conn.commit()

# Function to hash passwords
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Function to check passwords
def check_password(hashed_password, user_password):
    return bcrypt.checkpw(user_password.encode(), hashed_password.encode())

init(autoreset=True)  # Initialize colorama to auto-reset colors after each print statement

# Streamlit app header and instructions
st.markdown("<h1 style = 'text-align: center; color: #001e69;'>Welcome to the LETREP25 Project!</h1>", unsafe_allow_html=True)
st.subheader("Please login with your username and password below")
st.markdown("")

st.title("Login Page")


# Registration form
if 'register' not in st.session_state:
    st.session_state['register'] = False

if st.button('Register'):
    st.session_state['register'] = True

if st.session_state['register']:
    new_username = st.text_input('New Username')
    new_password = st.text_input('New Password', type='password')
    email = st.text_input('Email')
    if st.button('Submit Registration'):
        hashed_password = hash_password(new_password)
        c.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)', (new_username, hashed_password, email))
        conn.commit()
        st.success('User registered successfully')
# Button to display all users
#if st.button('Show All Users'):
    #c.execute('SELECT * FROM users')
    #users = c.fetchall()
    #for user in users:
        #st.write(user)

# Login form
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')

if st.button('Login'):
    c.execute('SELECT password, email FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    if result and check_password(result[0], password):
        st.success(f'Welcome {username}')
        st.session_state['logged_in'] = True
        st.session_state['username'] = username
        st.session_state['email'] = result[1]
    else:
        st.error('Username/password is incorrect')

# Forgot Password form
if 'forgot_password' not in st.session_state:
    st.session_state['forgot_password'] = False

if st.button('Forgot Password'):
    st.session_state['forgot_password'] = True

if st.session_state['forgot_password']:
    reset_username = st.text_input('Enter your username to reset password')
    new_password = st.text_input('Enter new password', type='password')
    if st.button('Submit New Password'):
        hashed_password = hash_password(new_password)
        c.execute('UPDATE users SET password = ? WHERE username = ?', (hashed_password, reset_username))
        conn.commit()
        st.success('Password reset successfully')
        st.session_state['forgot_password'] = False

# Profile management button
if st.session_state['logged_in']:
    if st.button('Manage Profile'):
        st.session_state['manage_profile'] = True

# Profile management section
if 'manage_profile' in st.session_state and st.session_state['manage_profile']:
    st.subheader("Profile")
    st.write(f"Username: {st.session_state['username']}")
    st.write(f"Email: {st.session_state['email']}")
    new_email = st.text_input('Update Email', value=st.session_state['email'])
    if st.button('Update Email'):
        c.execute('UPDATE users SET email = ? WHERE username = ?', (new_email, st.session_state['username']))
        conn.commit()
        st.session_state['email'] = new_email
        st.success('Email updated successfully')



# Function to process data
def process_data(file_name_imu00, file_name_imu01):
    column_names = ['col1', 'col2', 'col3', 'col4', 'col5', 'Xang', 'Yang', 'Zang', 'quat1', 'quat2', 'quat3', 'quat4']
    df00 = pd.read_csv(StringIO(file_name_imu00), header=None, names=column_names)
    df01 = pd.read_csv(StringIO(file_name_imu01), header=None, names=column_names)

    # Simulating the calculated angles (in degrees) for simplicity
    alpha = np.random.uniform(-90, 90, len(df00))  # Simulated flexion/extension
    beta = np.random.uniform(-45, 45, len(df00))   # Simulated lateral flexion
    gamma = np.random.uniform(-180, 180, len(df00))  # Simulated rotation

    return alpha, beta, gamma

# Function to plot pie charts
def plot_pie_chart(data, labels, title, ax):
    color1= ['#0077B5','#FFA500','#32CD32','#D16D9E']
    ax.pie(data, labels=labels, autopct='%1.1f%%', startangle=90, colors=color1)
    ax.set_title(title)

# Function to plot bar charts
def plot_bar_chart(data, labels, title, ax):
    color2= ['#0077B5','#FFA500','#32CD32','#D16D9E']
    ax.bar(labels, data, color=color2)
    ax.set_xlabel('Angle (°)')
    ax.set_ylabel('Count')
    ax.set_title(title)


st.title("Lumbar ROM")
st.subheader("Select each IMU file from the bucket")

# Select files from the S3 bucket 
aws_credentials = st.secrets["aws"]
access_key_id = aws_credentials["access_key_id"]
secret_access_key = aws_credentials["secret_access_key"]
region = aws_credentials["region"]
bucket_name = aws_credentials["bucket_name"]

#S3 client
session = boto3.Session(
    aws_access_key_id=access_key_id,
    aws_secret_access_key=secret_access_key,
    region_name=region
)
s3_client = session.client('s3')

# List files in S3 bucket
files = s3_client.list_objects_v2(Bucket=bucket_name).get('Contents', [])
file_names = [file['Key'] for file in files]

# Let the user select IMU files
uploaded_file_imu00 = st.selectbox("Select IMU00 CSV file", file_names)
uploaded_file_imu01 = st.selectbox("Select IMU01 CSV file", file_names)

# radio button to select type of plot
plot_type = st.radio("Select Plot Type", ('Pie Chart', 'Bar Graph'))

if uploaded_file_imu00 and uploaded_file_imu01:
    try:
        
        imu00_data = s3_client.get_object(Bucket=bucket_name, Key=uploaded_file_imu00)
        imu01_data = s3_client.get_object(Bucket=bucket_name, Key=uploaded_file_imu01)

        
        df_imu00 = imu00_data['Body'].read().decode('utf-8')
        df_imu01 = imu01_data['Body'].read().decode('utf-8')

        
        alpha, beta, gamma = process_data(df_imu00, df_imu01)

        # group angles
        alpha_bins = ['-90 to -45', '-45 to 0', '0 to 45', '45 to 90']
        beta_bins = ['-45 to -20', '-20 to 0', '0 to 20', '20 to 45']
        gamma_bins = ['-180 to -90', '-90 to 0', '0 to 90', '90 to 180']

        alpha_counts = pd.cut(alpha, bins=[-90, -45, 0, 45, 90]).value_counts()
        beta_counts = pd.cut(beta, bins=[-45, -20, 0, 20, 45]).value_counts()
        gamma_counts = pd.cut(gamma, bins=[-180, -90, 0, 90, 180]).value_counts()

        # plot
        fig, axs = plt.subplots(1, 3, figsize=(15, 5))

        if plot_type == 'Pie Chart':
            # Plot Pie charts
            plot_pie_chart(alpha_counts, alpha_bins, 'Forward Bend', axs[0])
            plot_pie_chart(beta_counts, beta_bins, 'Lateral Bend', axs[1])
            plot_pie_chart(gamma_counts, gamma_bins, 'Rotation', axs[2])
            
            

        elif plot_type == 'Bar Graph':
            # Plot Bar graphs
            plot_bar_chart(alpha_counts, alpha_bins, 'Flexion Bend', axs[0])
            plot_bar_chart(beta_counts, beta_bins, 'Lateral Bend', axs[1])
            plot_bar_chart(gamma_counts, gamma_bins, 'Rotation ', axs[2])

        # Adjust layout to prevent overlapping titles/labels
        plt.tight_layout()

        # Show the plot in Streamlit
        st.pyplot(fig)

        # Extract the base file name by removing "IMU" from the IMU file names
        base_name_imu00 = uploaded_file_imu00.replace('IMU', '').split('.')[0]
        base_name_imu01 = uploaded_file_imu01.replace('IMU', '').split('.')[0]

        # Option to download the processed data (for transparency or further analysis)
        processed_data = pd.DataFrame({
            'Alpha': alpha,
            'Beta': beta,
            'Gamma': gamma
        })
        csv_output = processed_data.to_csv(index=False)
        st.download_button(
            label="Download Processed Data",
            data=csv_output,
            file_name=f"{base_name_imu00}_processed_lumbar_data.csv",
            mime="text/csv"
        )

        # Save the plot figure to a BytesIO object
        img_bytes = BytesIO()
        fig.savefig(img_bytes, format='png')
        img_bytes.seek(0)  # Rewind the BytesIO object to the beginning

        # Option to download the plot image
        st.download_button(
            label="Download Plot Image",
            data=img_bytes,
            file_name=f"{base_name_imu00}_lumbar_rom_plot.png",
            mime="image/png"
        )

    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    st.warning("Please select both IMU files to process and display the results.")
