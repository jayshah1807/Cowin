import datetime
import json
import xml
import numpy as np
import requests
import pandas as pd
import streamlit as st
from copy import deepcopy
from fake_useragent import UserAgent
from footer_utils import image, link, layout,footer
import smtplib
from smtplib import SMTPException
import time
from smtplib import SMTP
from tabulate import tabulate
import mysql.connector
mydb = mysql.connector.connect(host = "us-cdbr-east-04.cleardb.com" ,user = "b78f4b602b5eaa", passwd = "4e66febc", database = "heroku_cc968c7647eee32")
mycursor = mydb.cursor()




# browser_header = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'}
# browser_header = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10; ONEPLUS A6000) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.99 Mobile Safari/537.36'}


st.set_page_config(layout='wide',
                   initial_sidebar_state='collapsed',
                   page_icon="https://www.cowin.gov.in/favicon.ico",
                   page_title="CoWIN Vaccination Slot Availability")

@st.cache(allow_output_mutation=True, suppress_st_warning=True)
def load_mapping():
    df = pd.read_csv("district_mapping.csv")
    return df

def filter_column(df, col, value):
    df_temp = deepcopy(df.loc[df[col] == value, :])
    return df_temp

def filter_capacity(df, col, value):
    df_temp = deepcopy(df.loc[df[col] > value, :])
    return df_temp

@st.cache(allow_output_mutation=True)
def Pageviews():
    return []

mapping_df = load_mapping()

rename_mapping = {
    'date': 'Date',
    'min_age_limit': 'Minimum Age Limit',
    'available_capacity': 'Available Capacity',
    'vaccine': 'Vaccine',
    'pincode': 'Pincode',
    'name': 'Hospital Name',
    'state_name' : 'State',
    'district_name' : 'District',
    'block_name': 'Block Name',
    'fee_type' : 'Fees'
    }

st.title('CoWIN Vaccination Slot Availability')
st.info('The CoWIN APIs are geo-fenced so sometimes you may not see an output! Please try after sometime ')

valid_states = list(np.unique(mapping_df["state_name"].values))

left_column_1, center_column_1, right_column_1 = st.beta_columns(3)
with left_column_1:
    numdays = st.slider('Select Date Range', 0, 10, 3)

with center_column_1:
    state_inp = st.selectbox('Select State', [""] + valid_states)
    if state_inp != "":
        mapping_df = filter_column(mapping_df, "state_name", state_inp)


mapping_dict = pd.Series(mapping_df["district id"].values,
                         index = mapping_df["district name"].values).to_dict()


unique_districts = list(mapping_df["district name"].unique())
unique_districts.sort()
with right_column_1:
    dist_inp = st.selectbox('Select District', unique_districts)

DIST_ID = mapping_dict[dist_inp]

base = datetime.datetime.today()
date_list = [base + datetime.timedelta(days=x) for x in range(numdays)]
date_str = [x.strftime("%d-%m-%Y") for x in date_list]

temp_user_agent = UserAgent()
browser_header = {'User-Agent': temp_user_agent.random}

final_df = None
for INP_DATE in date_str:
    URL = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={}&date={}".format(DIST_ID, INP_DATE)
    response = requests.get(URL, headers=browser_header)
    # print("response in text",response.text)
    if (response.ok) and ('centers' in json.loads(response.text)):
        resp_json = json.loads(response.text)['centers']
        # print("resp in json",resp_json)
        df = pd.DataFrame(resp_json)
        if resp_json is not None:
            if len(df):
                df = df.explode("sessions")
                df['min_age_limit'] = df.sessions.apply(lambda x: x['min_age_limit'])
                df['vaccine'] = df.sessions.apply(lambda x: x['vaccine'])
                df['available_capacity'] = df.sessions.apply(lambda x: x['available_capacity'])
                
                df['date'] = df.sessions.apply(lambda x: x['date'])
                df = df[["date", "available_capacity", "vaccine", "min_age_limit", "pincode", "name", "state_name", "district_name", "block_name", "fee_type"]]
                if final_df is not None:
                    final_df = pd.concat([final_df, df])
                else:
                    final_df = deepcopy(df)
        else:
            st.error("No rows in the data Extracted from the API")


if (final_df is not None) and (len(final_df)):
    final_df.drop_duplicates(inplace=True)
    final_df.rename(columns=rename_mapping, inplace=True)

    left_column_2, center_column_2, right_column_2, right_column_2a,  right_column_2b = st.beta_columns(5)
    with left_column_2:
        valid_pincodes = list(np.unique(final_df["Pincode"].values))
        pincode_inp = st.selectbox('Select Pincode', [""] + valid_pincodes)
        if pincode_inp != "":
            final_df = filter_column(final_df, "Pincode", pincode_inp)

    with center_column_2:
        valid_age = [18, 45]
        age_inp = st.selectbox('Select Minimum Age', [""] + valid_age)
        if age_inp != "":
            final_df = filter_column(final_df, "Minimum Age Limit", age_inp)

    with right_column_2:
        valid_payments = ["Free", "Paid"]
        pay_inp = st.selectbox('Select Free or Paid', [""] + valid_payments)
        if pay_inp != "":
            final_df = filter_column(final_df, "Fees", pay_inp)

    with right_column_2a:
        valid_capacity = ["Available"]
        cap_inp = st.selectbox('Select Availablilty', [""] + valid_capacity)
        if cap_inp != "":
            final_df = filter_capacity(final_df, "Available Capacity", 0)

    with right_column_2b:
        valid_vaccines = ["COVISHIELD", "COVAXIN"]
        vaccine_inp = st.selectbox('Select Vaccine', [""] + valid_vaccines)
        if vaccine_inp != "":
            final_df = filter_column(final_df, "Vaccine", vaccine_inp)

    table = deepcopy(final_df)
    table.reset_index(inplace=True, drop=True)
    st.table(table)
else:
    st.error("Unable to fetch data currently, please try after sometime")


user_input = st.text_input("Please Enter your Email Id to get Notification")
def msg():
    
    details = {
        "email": user_input,
        "pincode": pincode_inp
        }
    x= details.get("email")
    y =int(details.get("pincode"))
    mycursor.execute("""Insert into avail(email,pincode) values(%s,%s)""", (x,y))
    mydb.commit()
    print("Data Entered Successfully")
    
    for i in mycursor:
        print(i)
    

button = st.button('Send Availability')
if button:
    if valid_capacity != 0:
        msg()
        st.success("Thank you!!You will get SMS if their is Availibility")

today_date = datetime.date.today()
mycursor.execute("""Select * from avail""")
for k in mycursor:
    new_today_date = today_date.strftime("%d-%m-%Y")
    URL_GET = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByPin?pincode={}&date={}".format(k[1],new_today_date)
    # print(k)
    m = list(k)
    print(k)
    response = requests.get(URL_GET, headers=browser_header)
    # print("response in text",response.text)
    if (response.ok) and ('sessions' in json.loads(response.text)):
        resp_json = json.loads(response.text)['sessions']
        # print("resp in json",resp_json)
        avl_centers = []
        for data in resp_json:
            if  data['available_capacity'] > 0:
                avl_centers.append(data)
        
        if avl_centers:        
            sender = "vaccinebot.noreply@gmail.com"
                

            message = """From: From Person <vaccinebot.noreply@gmail.com>
                    
                            Subject: Vaccine Availability

                            The Availibility is:
                            %s
                        """ %(tabulate(avl_centers))

                
            smtpObj = smtplib.SMTP_SSL('smtp.gmail.com',465)
            smtpObj.login("vaccinebot.noreply@gmail.com", "V@ccinebot@187")
            
            smtpObj.sendmail(sender,k[0], message)         
            print("Successfully sent email")
time.sleep(60*120)
                
pageviews=Pageviews()
pageviews.append('dummy')
pg_views = len(pageviews)
footer(pg_views)
