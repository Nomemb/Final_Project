import React, { useState } from "react";
import LiveChatApp from "./components/LiveChat/LiveChatApp";
import ChatbotIcon from "./components/ChatbotIcon";
import ChatForm from "./components/ChatForm";
import ChatMessage from "./components/ChatMessage";

const App = () => {
  const [chatHistory, setChatHistory] = useState([
    {
      hideInChat: true,
      role: "model",
      text: "안녕하세요! 무엇을 도와드릴까요?",
    },
  ]);
  const [openScenario, setOpenScenario] = useState(null);
  const [toggleIndex, setToggleIndex] = useState(0);

  const handleToggle = (index, sIndex) => {
    console.log(`Toggling scenario for message ${index}, scenario ${sIndex}`);
    // 상태를 객체로 관리하여 특정 메시지의 시나리오 상태를 업데이트
    setOpenScenario(openScenario?.index === index && openScenario?.sIndex === sIndex ? null : { index, sIndex });
  };
  

  const generateBotResponse = async (userMessage) => {
    if (!userMessage.trim()) return;

    try {
      setChatHistory((prev) => [...prev, { role: "user", text: userMessage }]);
      setChatHistory((prev) => [
        ...prev,
        { role: "model", text: "Thinking..." },
      ]);

      const response = await fetch("http://localhost:8000/chatbot", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ user_message: userMessage }),
      });

      if (!response.ok) throw new Error("서버 오류가 발생했습니다.");

      const data = await response.json();

      setChatHistory((prev) =>
        prev
          .filter((msg) => msg.text !== "Thinking...")
          .concat([
            { role: "model", text: data.main_script },
            {
              role: "model",
              scenarios: data.sub_scenarios,
              isScenarios: true,
            },
          ])
      );
    } catch (error) {
      setChatHistory((prev) =>
        prev
          .filter((msg) => msg.text !== "Thinking...")
          .concat({
            role: "model",
            text: error.message,
            isError: true,
          })
      );
    }
  };


  const renderMessage = (chat, index) => {
    if (chat.isScenarios) {
      return (
        <div className="message bot-message" key={`scenarios-${index}`}>
          <ChatbotIcon />
          <div className="scenarios-container">
            {chat.scenarios.map((scenario, sIndex) => (
              <div key={sIndex} className="scenario">
                <button
                  className={`toggle-button ${
                    openScenario?.index === index && openScenario?.sIndex === sIndex ? "open" : ""
                  }`}
                  onClick={() => handleToggle(index, sIndex)}
                >
                  {scenario.title}
                </button>
                <br />
                {(openScenario?.index === index && openScenario?.sIndex === sIndex) && (
                  <div className="scenario-content">
                    {scenario.content.map((item, i) => (
                      <div key={i} className="content-item">
                        {item}
                      </div>
                    ))}
                    <div className="final-script">
                      <p>최종 답변 : <br /></p>
                      {scenario.final_script_ex} 
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      );
    }
  
    return <ChatMessage key={`${chat.role}-${index}`} chat={chat} />;
  };

  return (
    <>
      <header className="page-header">
        <img src="/logo.png" alt="Logo" className="logo-image" />
        <h1></h1>
      </header>

      <div className="app-container">
        <div className="live-chat-section">
          <LiveChatApp />
        </div>
        <div className="chatbot-section">
          <div className="chatbot-popup">
            <div className="chat-header">
              <div className="header-info">
                <ChatbotIcon />
                <h2 className="logo-text">Chatbot</h2>
              </div>
            </div>
            <div className="chat-body">
              {chatHistory.map((chat, index) => renderMessage(chat, index))}
            </div>
            <div className="chat-footer">
              <ChatForm
                chatHistory={chatHistory}
                setChatHistory={setChatHistory}
                generateBotResponse={generateBotResponse}
              />
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default App;
