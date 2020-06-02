import streamlit as st
import pandas as pd
from src.aws.nodemanager.nodemanager import Task
from src.aws.nodemanager.nodemanager import TaskPool

st.sidebar.title("Settings")
taskType=st.sidebar.selectbox("Data to upload",['CSV','Text'],index=1)

if taskType is 'CSV':
    uploaded_data=st.file_uploader("Choose a CSV file",type='csv')
    inputDataFrame=pd.read_csv(uploaded_data)
    task=Task(inputDataFrame,Task.CSV)
    TaskPool.add_task(task)
else:
    inputTextSnippet=st.text_area("Text to be classified")
    task=Task(inputTextSnippet,Task.TEXT)
    TaskPool.add_task(task)