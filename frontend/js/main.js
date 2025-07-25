import { BASE_API_URL } from './config.js';

document.addEventListener("DOMContentLoaded", () => {
  // 로그아웃 버튼 바인딩
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      sessionStorage.removeItem("token");
      sessionStorage.removeItem("chatHistory");
      window.location.href = "index.html";
    });
  }

  // profile.html에서만 내정보 불러오기
  if (window.location.pathname.endsWith("profile.html")) {
    const token = sessionStorage.getItem("token");
    if (!token) {
      alert("로그인이 필요합니다.");
      window.location.href = "index.html";
      return;
    }
    fetch(`${BASE_API_URL}/protected/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(res => {
        if (!res.ok) throw new Error("사용자 정보를 불러올 수 없습니다.");
        return res.json();
      })
      .then(data => {
        const user = data.user;
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        set("profile-id", user.user_id);
        set("profile-gender", user.gender);
        set("profile-age", user.age + "세");
        set("profile-height", user.height + "cm");
        set("profile-weight", user.weight + "kg");
        set("profile-level", user.level_desc || user.level);
        set("profile-injury-detail", user.injury_part || "없음");
      })
      .catch(err => {
        alert("내 정보를 불러오는 데 실패했습니다.");
        window.location.href = "index.html";
      });
  }

  const token = sessionStorage.getItem("token");

  if (!token) {
    alert("로그인이 필요합니다.");
    window.location.href = "index.html";
    return;
  }

  const welcomeMessage = document.getElementById("welcome-message");
  const chatWrapper = document.getElementById("chat-wrapper");
  const chatBox = document.getElementById("chat-box");
  const chatForm = document.getElementById("chat-form");
  const userInput = document.getElementById("userInput");
  const mainContent = document.querySelector(".main-content");
  const imageInput = document.getElementById("imageInput");
  const previewWrapper = document.getElementById("imagePreviewWrapper");
  const previewImage = document.getElementById("previewImage");
  const modelSelector = document.getElementById("modelSelector");
  const clearImageBtn = document.getElementById("clearImageBtn"); // 추가

  const profileBtn = document.getElementById("profileBtn");
  const modal = document.getElementById("profileModal");
  const profileDetails = document.getElementById("profileDetails");
  const closeModalBtn = document.querySelector(".close");

  let chatHistory = []; // 채팅 기록을 저장할 배열

  function formatMealPlan(mealPlanText) {
    const mealTypes = ["아침", "점심", "저녁", "간식"];
    let formattedHtml = '';
    let currentMealType = '';
    let currentMealItems = [];

    const lines = mealPlanText.split('\n')
                              .map(line => line.trim())
                              .filter(line => line.length > 0 && line !== "Meal Plan");

    lines.forEach(line => {
      let isMealTypeHeader = false;
      let foodItem = line;
      const parenthesisIndex = foodItem.indexOf('(');
      if (parenthesisIndex !== -1) {
        foodItem = foodItem.substring(0, parenthesisIndex).trim();
      }

      for (const type of mealTypes) {
        if (foodItem.startsWith(type + ':')) {
          if (currentMealType && currentMealItems.length > 0) {
            formattedHtml += `<h3>${currentMealType}</h3><ul>${currentMealItems.map(item => `<li>${item}</li>`).join('')}</ul>`;
          }
          currentMealType = type;
          currentMealItems = [];
          foodItem = foodItem.substring(type.length + 1).trim();
          currentMealItems.push(foodItem);
          isMealTypeHeader = true;
          break;
        }
      }
      if (!isMealTypeHeader) {
        if (currentMealType) {
          currentMealItems.push(foodItem);
        } else {
          formattedHtml += `<p>${line}</p>`;
        }
      }
    });

    if (currentMealType && currentMealItems.length > 0) {
      formattedHtml += `<h3>${currentMealType}</h3><ul>${currentMealItems.map(item => `<li>${item}</li>`).join('')}</ul>`;
    }
    return formattedHtml;
  }

  function appendMessage(sender, text, videos = [], elementToUpdate = null) {
    const msgContainer = elementToUpdate || document.createElement("div");

    if (!elementToUpdate) {
      msgContainer.className = `message ${sender}`;
    }

    msgContainer.innerHTML = ''; // Clear existing content before appending new

    // Check if the message contains a meal plan
    if (sender === 'bot' && text.includes("Daily Plan") && text.includes("Meal Plan")) {
      const parts = text.split("Meal Plan");
      const workoutPlanPart = parts[0];
      const mealPlanPart = "Meal Plan" + parts[1]; // Re-add "Meal Plan" header

      const workoutPlanNode = document.createElement("div");
      workoutPlanNode.innerHTML = workoutPlanPart.replace(/\n/g, '<br>'); // Preserve line breaks
      msgContainer.appendChild(workoutPlanNode);

      const mealPlanNode = document.createElement("div");
      mealPlanNode.innerHTML = formatMealPlan(mealPlanPart);
      msgContainer.appendChild(mealPlanNode);

    } else {
      const textNode = document.createElement("div");
      textNode.innerText = text;
      msgContainer.appendChild(textNode);
    }

    if (videos.length > 0) {
      const youtubeTitle = document.createElement("h4");
      youtubeTitle.className = "youtube-title";
      youtubeTitle.innerText = "추천 영상";
      msgContainer.appendChild(youtubeTitle);
      
      const youtubeVideosContainer = document.createElement("div");
      youtubeVideosContainer.className = "youtube-videos-container";
      videos.forEach(video => {
        const videoItem = document.createElement("div");
        videoItem.className = "youtube-video-item";

        const iframe = document.createElement("iframe");
        iframe.width = "100%";
        iframe.height = "200";
        iframe.src = `https://www.youtube.com/embed/${video.id}`;
        iframe.frameBorder = "0";
        iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
        iframe.allowFullscreen = true;
        videoItem.appendChild(iframe);

        const videoTitle = document.createElement("p");
        videoTitle.innerText = video.title;
        videoTitle.style.fontSize = "0.9em";
        videoTitle.style.marginTop = "5px";
        videoTitle.style.marginBottom = "15px";
        videoItem.appendChild(videoTitle);

        youtubeVideosContainer.appendChild(videoItem);
      });
      msgContainer.appendChild(youtubeVideosContainer);
    }

    if (!elementToUpdate) {
      chatBox.appendChild(msgContainer);
    }
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function saveChatHistory() {
    sessionStorage.setItem("chatHistory", JSON.stringify(chatHistory));
  }

  function loadChatHistory() {
    const savedChat = sessionStorage.getItem("chatHistory");
    if (savedChat) {
      try {
        chatHistory = JSON.parse(savedChat);
        chatBox.innerHTML = ''; // 기존 HTML 초기화
        chatHistory.forEach(msg => {
          // appendMessage를 사용하여 메시지 다시 렌더링
          appendMessage(msg.sender, msg.text, msg.videos || []);
        });
        mainContent.classList.add("chat-active");
        chatBox.scrollTop = chatBox.scrollHeight;
      } catch (e) {
        console.error("Failed to parse chat history from sessionStorage:", e);
        sessionStorage.removeItem("chatHistory"); // 파싱 실패 시 기록 삭제
        chatHistory = [];
      }
    }
  }

  // Load chat history on page load
  loadChatHistory();

  // 이미지 미리보기 초기화 함수
  function clearImagePreview() {
    imageInput.value = ""; // 파일 입력 필드 초기화
    previewImage.src = ""; // 미리보기 이미지 소스 초기화
    previewWrapper.classList.add("hidden"); // 미리보기 래퍼 숨기기
  }

  // "x" 버튼 클릭 시 미리보기 초기화
  clearImageBtn.addEventListener("click", clearImagePreview);

  imageInput.addEventListener("change", () => {
    const file = imageInput.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        previewImage.src = reader.result;
        previewWrapper.classList.remove("hidden");
      };
      reader.readAsDataURL(file);
    } else {
      clearImagePreview(); // 파일이 선택되지 않으면 미리보기 초기화
    }
  });

  chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const message = userInput.value.trim();
    const file = imageInput.files[0];

    if (!message && !file) return;

    if (welcomeMessage && !mainContent.classList.contains("chat-active")) {
      mainContent.classList.add("chat-active");
    }

    appendMessage("user", message || "[이미지 전송]"); // 사용자 메시지 추가
    chatHistory.push({ sender: "user", text: message || "[이미지 전송]", videos: [] }); // 사용자 메시지 저장
    saveChatHistory();
    userInput.value = "";

    const formData = new FormData();
    formData.append("message", message);
    if (file) formData.append("image", file);

    const model = modelSelector.value;
    formData.append("model", model);

    const botMessageDiv = document.createElement("div");
    botMessageDiv.className = "message bot";
    chatBox.appendChild(botMessageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    // YouTube videos container는 이제 appendMessage 내부에서 생성되므로 여기서 제거
    // const youtubeVideosContainer = document.createElement("div");
    // youtubeVideosContainer.className = "youtube-videos-container";
    // chatBox.appendChild(youtubeVideosContainer);

    let fullStreamBuffer = "";
    let youtubeVideos = []; // YouTube 영상 데이터를 저장할 배열

    try {
      const res = await fetch(`${BASE_API_URL}/chat/image`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (res.ok) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          let chunk = decoder.decode(value, { stream: true });
          botMessageDiv.textContent += chunk;
          fullStreamBuffer += chunk;
          chatBox.scrollTop = chatBox.scrollHeight;
        }
        
        // YouTube 검색 및 데이터 저장
        try {
            const youtubeSearchRes = await fetch(`${BASE_API_URL}/youtube_search?query=${encodeURIComponent(fullStreamBuffer)}`, {
                headers: { Authorization: `Bearer ${token}` },
            });

            if (youtubeSearchRes.ok) {
                const videoData = await youtubeSearchRes.json();
                if (videoData && videoData.length > 0) {
                    youtubeVideos = videoData; // YouTube 영상 데이터 저장
                }
            } else {
                console.error("Failed to fetch YouTube videos:", youtubeSearchRes.status, youtubeSearchRes.statusText);
            }
        } catch (youtubeErr) {
            console.error("Error fetching YouTube videos:", youtubeErr);
        }

        // 봇 메시지와 YouTube 영상을 함께 appendMessage로 전달하여 저장 및 렌더링
        appendMessage("bot", fullStreamBuffer, youtubeVideos, botMessageDiv); // 봇 메시지와 영상 함께 추가
        chatHistory.push({ sender: "bot", text: fullStreamBuffer, videos: youtubeVideos }); // chatHistory에 최종 메시지 저장
        saveChatHistory();

      } else {
        botMessageDiv.innerText = "❗ 오류가 발생했습니다.";
        chatHistory.push({ sender: "bot", text: "❗ 오류가 발생했습니다." }); // 오류 메시지도 저장
        saveChatHistory();
      }
    } catch (err) {
      botMessageDiv.innerText = "❗ 네트워크 오류입니다.";
      chatHistory.push({ sender: "bot", text: "❗ 네트워크 오류입니다." }); // 오류 메시지도 저장
      saveChatHistory();
      console.error(err);
    }

    clearImagePreview(); // 메시지 전송 후 미리보기 초기화
  });

  if (profileBtn) {
    profileBtn.addEventListener("click", async () => {
      try {
        const res = await fetch(`${BASE_API_URL}/protected/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!res.ok) throw new Error("사용자 정보를 불러올 수 없습니다.");

        const data = await res.json();
        const user = data.user;

        profileDetails.innerHTML = `
          <div class="info-group"><div class="label">아이디</div><div class="value">${user.user_id}</div></div>
          <div class="info-group"><div class="label">성별</div><div class="value">${user.gender}</div></div>
          <div class="info-group"><div class="label">나이</div><div class="value">${user.age}세</div></div>
          <div class="info-group"><div class="label">키</div><div class="value">${user.height}cm</div></div>
          <div class="info-group"><div class="label">몸무게</div><div class="value">${user.weight}kg</div></div>
          <div class="divider"></div>
          <div class="info-group"><div class="label">운동 수준</div><div class="value">${user.level}</div></div>
          <div class="info-group"><div class="label">부상 부위</div><div class="value">${user.injury_part || "없음"}</div></div>
          <div class="info-group"><div class="label">부상 수준</div><div class="value">${user.injury_level || "없음"}</div></div>
        `;

        modal.classList.remove("hidden");
      } catch (err) {
        alert("내 정보를 불러오는 데 실패했습니다.");
        console.error(err);
      }
    });
  }

  closeModalBtn.addEventListener("click", () => modal.classList.add("hidden"));
  window.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.add("hidden");
  });
});