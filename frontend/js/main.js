// js/main.js

document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");
  const chatBox = document.getElementById("chat-box");
  const userInput = document.getElementById("userInput");
  const sendBtn = document.getElementById("sendBtn");
  const logoutBtn = document.getElementById("logoutBtn");  
  const profileBtn = document.getElementById("profileBtn");

  if (!token) {
    alert("로그인이 필요합니다.");
    window.location.href = "index.html";
    return;
  }

  logoutBtn.addEventListener("click", () => {
    localStorage.removeItem("token");
    window.location.href = "index.html";
  });

  function appendMessage(sender, text) {
    const msg = document.createElement("div");
    msg.className = `message ${sender}`;
    msg.innerText = text;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  sendBtn.addEventListener("click", async () => {
    const message = userInput.value.trim();
    if (!message) return;

    appendMessage("user", message);
    userInput.value = "";

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ message })
      });

      if (res.ok) {
        const data = await res.json();
        appendMessage("bot", data.response);
      } else {
        appendMessage("bot", "❗ 에러가 발생했습니다.");
      }
    } catch (err) {
      appendMessage("bot", "❗ 네트워크 오류입니다.");
      console.error(err);
    }
  });
});