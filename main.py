from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import asyncio
import json

# FastAPI 앱 생성
app = FastAPI()

# CORS 설정 (React 프론트엔드와 연결)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 origin 허용으로 변경
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 대화 요청 모델 정의
class ChatMessage(BaseModel):
    message: str  # 대화 내용

# 루트 경로 정의 (404 방지)
@app.get("/")
async def root():
    return {"message": "FastAPI 서버가 정상적으로 작동 중입니다."}

# ==================================  OBSOLETE ===================================
# WebSocket을 통한 대화 데이터 스트리밍
class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# WebSocket 연결 관리
import json  # JSON 사용 추가

@app.websocket("/chat")
async def chat(websocket: WebSocket):

    # 대화 데이터 저장용 리스트
    dialog = []
    await manager.connect(websocket)  # 클라이언트 연결
    try:
        sent_length = 0  # 이미 보낸 메시지 개수 추적

        while True:
            # 새로운 메시지가 추가되었는지 확인
            if len(dialog) > sent_length:
                role, message = dialog[sent_length]
                now = datetime.now().strftime("%H:%M:%S")
                if role == "고객":
                    position = "left" # 고객 말풍선 왼쪽
                    label = f"[고객:1234] {now}"
                elif role == "상담사":
                    position = "right" # 상담사 말풍선 오른쪽
                    label = f"[상담사:김상담] {now}"
                else:
                    position = "center"
                    label = "[알 수 없음]"

                # 메시지를 JSON 형식으로 전송
                await websocket.send_text(
                    json.dumps({"label": label, "position": position, "message": message.strip()})
                )
                sent_length += 1

                # 상담 종료 메시지가 있는 경우
                if message.strip().lower() == "상담 종료":
                    # 종료 메시지 전송
                    await websocket.send_text(
                        json.dumps({"label": "종료", "position": "center", "message": "상담이 종료되었습니다."})
                    )
                    # 루프 종료
                    break

            # 새로운 메시지가 없으면 대기
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        print("클라이언트와의 연결이 끊어졌습니다.")
    finally:
        # 종료 후 연결 해제
        manager.disconnect(websocket)

# ==================================  OBSOLETE ===================================

# 연결된 WebSocket 클라이언트 저장
connected_clients = set()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        connected_clients.add(websocket)
        print(f"New client connected. Total clients: {len(connected_clients)}")
        
        while True:
            try:
                data = await websocket.receive_text()
                print(f"Received: {data}")
            except WebSocketDisconnect:
                break
    finally:
        connected_clients.remove(websocket)
        print(f"Client disconnected. Remaining clients: {len(connected_clients)}")

# 고객 메시지 추가 엔드포인트
@app.post("/chat/customer")  # @app.websocket("/ws") 데코레이터 제거
async def input_customer_dialog(voice: ChatMessage):
    print(f"Received customer input: {voice.message}")

    now = datetime.now().strftime("%H:%M:%S")
    position = "left"
    label = f"[고객:1234] {now}"
    message = voice.message

    for client in connected_clients:
        print(client)
        await client.send_text(json.dumps({
            "label": label, 
            "position": position, 
            "message": message.strip()
        }))

    return {"message": "고객 메시지가 성공적으로 추가되었습니다."}

# 상담사 메시지 추가 엔드포인트
@app.post("/chat/agent")
async def input_agent_dialog(voice: ChatMessage):
    print(f"Received agent input: {voice.message}")
    now = datetime.now().strftime("%H:%M:%S")
    message_data = {
        "label": f"[상담사:김상담] {now}",
        "position": "right",
        "message": voice.message.strip()
    }

    # 상담 종료 처리
    if voice.message.strip() == "상담 종료":
        # 종료 메시지로 변경
        message_data.update({
            "label": "",
            "position": "center",
            "message": "상담이 종료되었습니다."
        })
        
        # 종료 메시지 전송 및 연결 종료
        disconnected = set()
        for client in connected_clients:
            try:
                await client.send_text(json.dumps(message_data))
                await client.close()
                disconnected.add(client)
            except:
                disconnected.add(client)
        
        # 끊어진 연결 제거
        connected_clients.difference_update(disconnected)
        
        return {"message": "상담이 종료되었습니다."}

    # 일반 메시지 전송
    disconnected = set()
    for client in connected_clients:
        try:
            await client.send_text(json.dumps(message_data))
        except:
            disconnected.add(client)
    
    # 끊어진 연결 제거
    connected_clients.difference_update(disconnected)

    return {"message": "상담사 메시지가 성공적으로 추가되었습니다."}


from pages.model_query import find_similar_doc_from_db

class ChatbotQueryInput(BaseModel):
    user_message: str  # The field is fixed and required

@app.post("/chatbot")
async def chatbot_query(query_input: ChatbotQueryInput):
    user_message = query_input.user_message
    try:
        answer = find_similar_doc_from_db(user_message)
        print(f"answer: ", answer)

        return answer
    except Exception as e:
        return {
            "status": "error",
            "bot_response": str(e)
        }

@app.post("/chatbot_mockup")
async def chatbot_query(query_input: ChatbotQueryInput):
    return {
        "status": "success", 
        "main_script" : 
            "불편을 드려 죄송합니다. \n \
            주문 상태가 `배송 준비 중`이라 배송이 지연되는 점, \n \
            우선 양해 부탁드립니다. \n \
            정확한 상담을 위해 주문하신 주문 번호 확인 부탁드립니다.",
        "sub_scenarios": [
            {
                "title": "[로켓배송 상품01]", 
                "content": [
                    "1. 주문번호 확인", 
                    "2. 배송 현황을 시스템에서 직접 확인하고,", 
                    "3. 지연 사유(악천후, 주문량 증가 등)를 안내합니다.", 
                    "4. 예상 배송일을 다시 안내하거나, \n \
                        문제 해결을 위해 최선을 다하겠다고 설명"
                ]
                , "final_script_ex": "예상 배송일은 X월 X일로 확인됩니다."
            }, 
            {
                "title": "[로켓배송 상품02]", 
                "content": [
                    "1. ㅋㅋ 주문번호 확인", 
                    "2. ㅋㅋ 배송 현황을 시스템에서 직접 확인하고,", 
                    "3. ㅋㅋ 지연 사유(악천후, 주문량 증가 등)를 안내합니다.", 
                    "4. ㅋㅋ 예상 배송일을 다시 안내하거나, \n \
                        \t 문제 해결을 위해 최선을 다하겠다고 설명"
                ]
                , "final_script_ex": "ㅋㅋ 예상 배송일은 X월 X일로 확인됩니다."
            }, 
        ]
    }

# 실행 명령어
# uvicorn main:app --port 8002 --reload
# npm start

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", reload=True)
