import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import numpy as np


def plot_training_results(history):
    acc = history['acc']
    acc_chart = pd.DataFrame(history['val_acc'], columns=['validation accuracy'])
    st.line_chart(acc_chart)
