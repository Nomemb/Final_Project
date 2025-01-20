import React, { useEffect, useState } from "react";
import "./LiveChat.css";

function LiveChatApp() {
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(false);
  const [ended, setEnded] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    let reconnectAttempt = 0;
    const maxReconnectAttempts = 5;

    const websocket = new WebSocket("ws://127.0.0.1:8000/ws");

        websocket.onopen = () => {
          console.log("상담이 연결되었습니다.");
          setError(false);
          setIsConnected(true);
          reconnectAttempt = 0;
    };

    websocket.onerror = (error) => {
      console.error("WebSocket 에러 발생:", error);
      setError(true);
      setIsConnected(false);
    };

    websocket.onclose = () => {
      console.log("WebSocket 연결이 종료되었습니다.");
      setIsConnected(false);

      if (!ended && reconnectAttempt < maxReconnectAttempts) {
        console.log(
          `재연결 시도 ${reconnectAttempt + 1}/${maxReconnectAttempts}`
        );
        reconnectAttempt++;
        setTimeout(connectWebSocket, 3000);
      } else if (!ended) {
        setError(true);
      }
    };

    websocket.onmessage = (event) => {
      try {
        console.log("Received message:", event.data); // OK
        const parsedMessage = JSON.parse(event.data);
        const { label, position, message } = parsedMessage;

        setMessages((prevMessages) => [
          ...prevMessages,
          { label, position, message },
        ]);

        if (
          label === "종료" &&
          position === "center" &&
          message === "상담이 종료되었습니다."
        ) {
          setEnded(true);
          websocket.close();
        }
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    };

    return () => {
        websocket.close();
    };
  }, [ended]);
  

  return (
    <div className="live-chat-container">
      <div className="live-chat-wrapper">
        <div className="live-chat-header">
          실시간 대화록
          {isConnected && (
            <span className="connection-status connected"> ●</span>
          )}
          {!isConnected && (
            <span className="connection-status disconnected"> X</span>
          )}
        </div>
        <div className="live-chat-messages">
          {messages.map((msg, index) => (
            <div key={index} className={`live-chat-message ${msg.position}`}>
              <div className="live-chat-label">{msg.label}</div>
              <div className="live-chat-bubble">{msg.message}</div>
            </div>
          ))}
        </div>
        {error && !ended && (
          <div className="live-chat-error">
            서버와의 연결이 끊어졌습니다. 연결을 복구 중입니다...
          </div>
        )}
        {ended && <div className="live-chat-ended">상담이 종료되었습니다.</div>}
      </div>
    </div>
  );
}

export default LiveChatApp;

