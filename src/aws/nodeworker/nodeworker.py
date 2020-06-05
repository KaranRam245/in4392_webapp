"""
Module for the Node Worker.
"""
from aws.utils.monitor import Observable, Listener
from src.models.Senti import Senti
from src.data.Glove import Glove
from src.data import Tokenize
from src.aws.utils.state import TaskState
from src.aws.nodemanager.nodemanager import Task
from tensorflow.keras.models import load_model
import os

class WorkerCore(Observable):
    """
    The WorkerCore accepts the task from the Node Manager.
    """

    def run(self, task:Task, model_path:str, tokenizer_path:str):
        """
        Start function for the WorkerCore.
        """

        input_sequences= Tokenize.tokenize_text(tokenizer_path,task.get_task_data())
        model=load_model(model_path
        labels=model.predict(input_sequences)
        
        return task.get_task_data(),labels
    

class WorkerMonitor(Listener):

    def __init__(self):
        pass

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format.
        """
        raise NotImplementedError("The class is a listener but has not implemented the event "
                                  "method.")

