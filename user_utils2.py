#Pinecone team has been making a lot of changes to there code and here is how it should be used going forward :)
from pinecone import Pinecone as PineconeClient
#from langchain.vectorstores import Pinecone     #This import has been replaced by the below one :)
from langchain_community.vectorstores import Pinecone
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
#from langchain.llms import OpenAI #This import has been replaced by the below one :)
from langchain_openai import OpenAI
from langchain.chains.question_answering import load_qa_chain
#from langchain.callbacks import get_openai_callback #This import has been replaced by the below one :)
from langchain_community.callbacks import get_openai_callback
from langchain_community.llms import HuggingFaceEndpoint
from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.chains import RetrievalQA
import joblib
from pages.admin_utils2 import *
from langchain.schema.messages import HumanMessage as hm, SystemMessage, AIMessage
from transformers import pipeline
from langchain.llms import HuggingFacePipeline
from langchain.prompts.prompt import PromptTemplate
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain.schema import format_document
from langchain_core.messages import AIMessage, HumanMessage, get_buffer_string
from langchain_core.runnables import RunnableParallel
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain.memory import ConversationBufferMemory
from operator import itemgetter
from dotenv import load_dotenv
from langchain.chains import ConversationalRetrievalChain


def create_embedding():
    embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    return embeddings

def define_rag_chain():
    load_dotenv()
    model_name = "mistralai/Mistral-7B-Instruct-v0.2"
    vectorstore = Chroma(persist_directory='db', embedding_function=SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2"))
    retriever = get_retriever(vectorstore)

    llm = HuggingFaceEndpoint(repo_id="mistralai/Mistral-7B-Instruct-v0.2", temperature=0.1)

    memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True)

    ### Contextualize question ###
    _template = """
    [INST] 
    Given the following conversation and a follow up question, 
    rephrase the follow up question to be a standalone question, in its original language, 
    that can be used to query a Chroma DB index. This query will be used to retrieve documents with additional context.

    Let me share a couple examples.

    If you do not see any chat history, you MUST return the "Follow Up Input" as is:
    ```
    Chat History:
    Follow Up Input: How is Lawrence doing?
    Standalone Question:
    How is Lawrence doing?
    ```

    If this is the second question onwards, you should properly rephrase the question like this:
    ```
    Chat History:
    Human: How is Lawrence doing?
    AI: 
    Lawrence is injured and out for the season.
    Follow Up Input: What was his injury?
    Standalone Question:
    What was Lawrence's injury?
    ```

    Now, with those examples, here is the actual chat history and input question.
    Chat History:
    {chat_history}
    Follow Up Input: {question}
    Standalone question:
    [your response here]
    [/INST] 
    """

    # Define a custom template for the question prompt
    custom_template = """Given the following conversation and a follow-up question, \
                        rephrase the follow-up question to be a standalone question, \
                        in its original English.
                            Chat History:
                            {chat_history}
                            Follow-Up Input: {question}
                            Standalone question:"""

    # Create a PromptTemplate from the custom template
    CUSTOM_QUESTION_PROMPT = PromptTemplate.from_template(custom_template)  

    # Create a ConversationalRetrievalChain from an LLM with the specified components
    conversational_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        memory=memory,
        condense_question_prompt=CUSTOM_QUESTION_PROMPT
    )

    return conversational_chain



def get_answer(user_input, rag_chain):    
    ### Manage chat history ###
    
    ai_msg = rag_chain({"question": user_input})
    ai_msg = ai_msg["answer"]
    return ai_msg


def convert_message(m):
    if m["role"] == "user":
        return hm(content=m["content"])
    elif m["role"] == "assistant":
        return AIMessage(content=m["content"])
    elif m["role"] == "system":
        return SystemMessage(content=m["content"])
    else:
        raise ValueError(f"Unknown role {m['role']}")



def _format_chat_history(chat_history):
    def format_single_chat_message(m):
        if type(m) is hm:
            return "Human: " + m.content
        elif type(m) is AIMessage:
            return "Assistant: " + m.content
        elif type(m) is SystemMessage:
            return "System: " + m.content
        else:
            raise ValueError(f"Unknown role {m['role']}")

    return "\n".join([format_single_chat_message(m) for m in chat_history])


def predict(query_result):
    Fitmodel = joblib.load('modelsvm.pk1')
    result=Fitmodel.predict([query_result])
    return result[0]