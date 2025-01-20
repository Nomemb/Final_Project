import os 
import dotenv 
from pprint import pprint
import hashlib
import json

from langchain_upstage import UpstageEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough

from sqlalchemy import create_engine, text 
from sqlalchemy.sql import select

from .credentials import user_id, user_pw, endpoint, port, db

def get_db_connection():
    dotenv.load_dotenv()
    print(f"database: ", db)
    # MySQL 연결 설정
    DATABASE_URL = f"mysql+pymysql://{user_id}:{user_pw}@{os.environ.get('RDS_ENDPOINT')}:{port}/{db}"  # 실제 연결 정보로 변경
    engine = create_engine(DATABASE_URL, pool_recycle=600)
    conn = engine.connect()
    return engine, conn

def merge_pages(pages):
    merged = "\n\n".join(page.page_content for page in pages)
    return merged

def model_initialize():
    dotenv.load_dotenv()

    # GPT_API_KEY = os.environ.get("OPENAI_API_KEY")
    UPSTAGE_API_KEY = os.environ.get("UPSTAGE_API_KEY")
    PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")

    # 만들어 놓은 DB가 있을 때
    index_name = 'upstage-index'
    # Upstage 에서 제공하는 Embedding Model을 활용
    embedding = UpstageEmbeddings(model="solar-embedding-1-large",
                                api_key=UPSTAGE_API_KEY)
    
    # VectorStore도 이미 Pinecone에 있다고 가정하고 가져오는 것으로 시작하는 단계 
    database = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embedding)

    # ChatGoogleGenerativeAI 언어 모델을 초기화합니다.
    model = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest",  # 사용할 모델을 지정합니다.
    )

    retriever = database.as_retriever(
        search_type="mmr", search_kwargs={"k": 4, "fetch_k": 5}
    )

    template = """
    [context]: {context}
    ---
    [질의]: {query}

    7년 이상의 경력을 가진 상담사라고 생각하고, 위의 [context] 정보 내에서 [질의]에 대해 상담사 입장에서 사용자가 만족할 수 있을 정도로 성의있게 답해주세요.
    최대한 문장을 쉼표로 끊어서 대답하기 보다는 온점으로 문장을 끊어주세요. 
    문장의 마무리는 '~요' 보다는 '~다'로 끝나는 쪽이 전문적으로 보입니다.

    또한, 상담사는 가능한 선에서 직접 확인+안내+해결을 도와주는 직원이므로 직접 확인 후 해결까지 돕는 방향으로 작성해 주세요.
    그리고, 사용자의 편의를 위해 서비스 특성 상 쿠션어를 사용하시면 좋습니다.
    쿠션어의 예시는 다음과 같습니다.
    예시)
    불편을 드려 죄송합니다.
    번거로우시겠지만~
    ~하는 점 양해 부탁드립니다.
    ~할 예정입니다.
    ~를 부탁드립니다.

    위 사항들을 종합해서 2~3줄로 상담사가 활용하기 좋게 대본을 만들어 주세요.
    대본을 만들면 대본의 마침표가 나올때마다 보기 쉽게 실제 줄바꿈을 해주세요.

    만약, 조건별로 안내 내용이 다른 경우
    1차 응대 (양해멘트 or 1차 안내 등) + 정보 확인 멘트로 대본을 구성하면 됩니다.
    정보 확인 멘트는 "정확한 상담을 위해 주문하신 주문 번호 확인 부탁드립니다." 입니다.
    문서의 아래에 각 조건별 대응 방법을 기술해 주세요.
    그리고 조건별 안내 내용은 간결하게 내용만말해줘.

    단, 제일 중요한 것은 [context] 정보에 없는 내용을 답해서는 안됩니다. [context]에 정보가 없거나 문서들의 유사성이 0.2 이하로 떨어질 경우, "문의주신 내용은 확인이 필요하여 지금 답변드리기 어려울 것 같습니다. 번거로우시겠지만 확인 후에 다시 연락드려도 괜찮을까요?" 라고 답해주세요.


    format instructions: {format_instruction}
    sub_scenarios에 들어갈 조건별 대응 방법들이 많은 경우, 더 추가해도 됩니다.
    """

    format_instruction = """
    {
        "main_script" : 
                "불편을 드려 죄송합니다. 주문 상태가 '배송 준비 중'인데 배송이 지연되어 답답하시죠? 정확한 상담을 위해 주문하신 주문 번호 확인 부탁드립니다.",
        "sub_scenarios": [
            {
                "title": "[로켓배송 상품]", 
                "content": [
                        "1. 주문번호 확인", 
                        "2. 배송 현황을 시스템에서 직접 확인,", 
                        "3. 지연 사유(악천후, 주문량 증가 등)를 안내.", 
                        "4. 예상 배송일을 다시 안내하거나, 문제 해결을 위해 최선을 다하겠다고 설명"
                ]
                , "final_script_ex": "예상 배송일은 X월 X일로 확인됩니다."
            }, 

            {
                "title": "[로켓배송 상품]", 
                "content": [
                        "1. 주문번호 확인", 
                        "2. 배송 현황을 시스템에서 직접 확인,", 
                        "3. 지연 사유(악천후, 주문량 증가 등)를 안내.", 
                        "4. 예상 배송일을 다시 안내하거나, 문제 해결을 위해 최선을 다하겠다고 설명" 
                ]      
                , "final_script_ex": "예상 배송일은 X월 X일로 확인됩니다."
            }, 
        ]
    }
    """

    prompt = ChatPromptTemplate.from_template(template,
                                            partial_variables={"format_instruction":format_instruction})

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)

    def merge_pages(pages):
        merged = "\n\n".join(page.page_content for page in pages)
        return merged


    chain = (
        {"query": RunnablePassthrough(), "context": retriever | merge_pages}
        | prompt
        | llm
        | JsonOutputParser()
    )

    # VectorStore, RAG, Langchain
    return database, retriever, chain

"""
Initialize
"""
database, retriever, chain = model_initialize()
engine, conn = get_db_connection()


# functions
def get_doc_from_rag(query: str):
    if query is None: 
        raise Exception("Query Not init to RAG")

    results = database.similarity_search_with_score(query=query, k=3)

    return ",".join(sorted([hashlib.md5(result.page_content.encode()).hexdigest() for result in database.similarity_search(query=query, k=3)]))
    # 9e08ee6d1e8333375ef21a8eb98206fd,b5ace08316bde547ddba86e77ebbe897,d1f369d3e35f14c96275cf42d809c6f1

def transform_results_to_dict(results):
    # 결과를 테이블 구조에 맞는 딕셔너리로 변환
    dict_list = []
    
    for row in results:
        # row의 각 항목을 딕셔너리의 키-값으로 매핑
        row_dict = {
            'id': row[0],
            'created_at': row[1],  # datetime 객체 그대로 저장
            'query': row[2],
            'hashed_docs': row[3],
            'created_answer': row[4]
        }
        dict_list.append(row_dict)
    
    return dict_list


# sqlalchemy 연결
def find_similar_doc_from_db(query: str):
    hashed_from_rag = get_doc_from_rag(query)
    print("hashed query: ", hashed_from_rag)

    with engine.connect() as conn:

        similar_queries = conn.execute(text("SELECT * FROM cache WHERE hashed_docs = :hash"), {"hash": hashed_from_rag}).fetchall()

        results = transform_results_to_dict(similar_queries)

        # 있는 지 판단 
    if not len(results):
        return get_message_from_llm(query)
    
    # json 형태를 문자열로 변환해서 저장했기 때문에 
    # 해당 문자열을 받아와서 다시 json 통해 python-dict로 변환 후 리턴 
    return json.loads(results[0]['created_answer'])


def get_message_from_llm(query: str):
    print("llm invoked - query: ", query)

    # TODO : Model 돌리기
    # 모델 돌린 결과 
    # 얘는 miss니까 새로 적재하는 sql insert 과정이 추가로 필요
    query_relevant_docs_hashed = get_doc_from_rag(query)

    # LLM 모델 호출
    generated_answer = chain.invoke(query)

    # TODO : 문자열로 바꿔서 TEXT 자료형에 넣기
    json_str_answer = json.dumps(generated_answer, ensure_ascii=False)
    
    print("-" * 80) 
    print(type(json_str_answer))
    print(json_str_answer)

    # TODO : 저장하기 
    with engine.connect() as conn:
        # 트랜잭션 시작
        with conn.begin():
            # INSERT INTO 구문 실행
            conn.execute(
                text(
                    """
                    INSERT INTO cache (created_at, query, hashed_docs, created_answer)
                    VALUES (
                        now(), 
                        :query, 
                        :hash, 
                        :answer 
                    );
                    """
                ),
                {
                    "query": query, 
                    "hash": query_relevant_docs_hashed, 
                    "answer": json_str_answer
                }
            )
            # commit() 호출이 필요 없음, with block이 끝나면 자동으로 commit됩니다.
    
    return generated_answer