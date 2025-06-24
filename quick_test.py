from llm_provider import get_llm
llm = get_llm()
print("Assistant:", llm.invoke("Say hello as JSON").content)