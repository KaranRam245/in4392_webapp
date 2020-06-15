import streamlit as st
import pandas as pd
from src.aws.nodemanager.nodemanager import Task
from src.aws.nodemanager.nodemanager import TaskPool
import base64
def get_table_download_link(df):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
    return f'<a href="data:file/csv;base64,{b64}">Download csv file</a>'

st.sidebar.title("Settings")
taskType=st.sidebar.selectbox("Data to upload",['CSV','Text'],index=1)
task=""
if taskType is 'CSV':
    uploaded_data=st.file_uploader("Choose a CSV file",type='csv')
    if uploaded_data:
        st.markdown()
        inputDataFrame=pd.read_csv(uploaded_data)
        task=Task(inputDataFrame,Task.CSV)
    # TaskPool.add_task(task)
else:
    inputTextSnippet=st.text_area("Text to be classified")
    task=Task(inputTextSnippet,Task.TEXT)
    # TaskPool.add_task(task)

# text,labels="OUTPUT FROM WORKER RUN COMES HERE"
example_output= pd.DataFrame({"Text":["lkjsdlkasjdklajldaskjdal"], "Toxic":[1],"Severe_Toxic":[0],"Obscene":[1],"Insult":[1],"Threat":[0],"Identity_Hate":[0]})
toxic='<mark style="background-color:gray;">Toxic</mark>'if True else '<mark style="background-color:green;">Toxic</mark>'
severe_toxic='<mark style="background-color:gray;">Toxic</mark>'if False else '<mark style="background-color:green;">Toxic</mark>'
obscene='<mark style="background-color:gray;">Obscene</mark>'if True else '<mark style="background-color:green;">Obscene</mark>'
threat='<mark style="background-color:gray;">Threat</mark>'if True else '<mark style="background-color:green;">Threat</mark>'
insult='<mark style="background-color:gray;">Insult</mark>'if False else '<mark style="background-color:green;">Insult</mark>'
identity_hate='<mark style="background-color:gray;">Identity Hate</mark>'if True else '<mark style="background-color:green;">Identity Hate</mark>'

if(task):
    result =task.get_task_data()
    st.markdown(f'<p>{toxic}{severe_toxic}{obscene}{threat}{insult}{identity_hate}</p>', unsafe_allow_html=True)
    st.markdown(get_table_download_link(example_output), unsafe_allow_html=True)