import { BASE_API_URL } from './config.js';

// IndexedDB 설정
const DB_NAME = 'GymPTChatDB';
const DB_VERSION = 1;
const STORE_NAME = 'ttsAudio';

let db;

function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };

    request.onsuccess = (event) => {
      db = event.target.result;
      resolve(db);
    };

    request.onerror = (event) => {
      console.error("IndexedDB error:", event.target.errorCode);
      reject("IndexedDB error");
    };
  });
}

async function addAudio(key, audioBlob) {
  const database = await openDb();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    const request = store.put(audioBlob, key);

    request.onsuccess = () => resolve();
    request.onerror = (event) => reject(event.target.error);
  });
}

async function getAudio(key) {
  const database = await openDb();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction([STORE_NAME], 'readonly');
    const store = transaction.objectStore(STORE_NAME);
    const request = store.get(key);

    request.onsuccess = () => resolve(request.result);
    request.onerror = (event) => reject(event.target.error);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const token = sessionStorage.getItem("token");

  // 공통 로직: 로그아웃 버튼 처리
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      sessionStorage.removeItem("token");
      sessionStorage.removeItem("chatHistory");
      window.location.href = "index.html";
    });
  }

  // --- 채팅 페이지 (main.html) 전용 로직 ---
  if (window.location.pathname.endsWith("main.html") || window.location.pathname.endsWith("/")) {
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
    const clearImageBtn = document.getElementById("clearImageBtn");
    const profileBtn = document.getElementById("profileBtn");
    const modal = document.getElementById("profileModal");
    const profileDetails = document.getElementById("profileDetails");
    const closeModalBtn = document.querySelector(".close");

    let chatHistory = [];
    let currentAudio = null;
    let currentPlayingAudioKey = null;

    function updatePlayButtonState(audioKey, isPlaying) {
        const allPlayButtons = document.querySelectorAll('.play-button-wrapper');
        allPlayButtons.forEach(wrapper => {
            const key = wrapper.dataset.audioKey;
            if (key === audioKey) {
                if (isPlaying) {
                    wrapper.innerHTML = `
                        <button class="play-button" title="음성 정지">
                            <svg width="20" height="20" viewBox="0 0 24 24"><path d="M6 6h12v12H6z" fill="currentColor"/></svg>
                        </button>
                        <span class="play-button-text">정지</span>
                    `;
                } else {
                    wrapper.innerHTML = `
                        <button class="play-button" title="음성 재생">
                            <svg width="20" height="20" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>
                        </button>
                        <span class="play-button-text">음성으로 듣기</span>
                    `;
                }
            } else if (wrapper.querySelector('svg path[d="M6 6h12v12H6z"]')) {
                wrapper.innerHTML = `
                    <button class="play-button" title="음성 재생">
                        <svg width="20" height="20" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>
                    </button>
                    <span class="play-button-text">음성으로 듣기</span>
                `;
            }
        });
    }

    async function playAudio(audioKey) {
        if (currentAudio && currentPlayingAudioKey === audioKey) {
            if (currentAudio.paused) {
                currentAudio.play().catch(e => console.error("Error playing audio:", e));
                updatePlayButtonState(audioKey, true);
            } else {
                currentAudio.pause();
                updatePlayButtonState(audioKey, false);
            }
            return;
        }

        if (currentAudio) {
            currentAudio.pause();
            currentAudio.currentTime = 0;
            updatePlayButtonState(currentPlayingAudioKey, false);
            URL.revokeObjectURL(currentAudio.src);
            currentAudio = null;
            currentPlayingAudioKey = null;
        }

        const audioBlob = await getAudio(audioKey);
        if (audioBlob) {
            const audioUrl = URL.createObjectURL(audioBlob);
            currentAudio = new Audio(audioUrl);
            currentPlayingAudioKey = audioKey;

            currentAudio.play().catch(e => {
                console.error("Error playing audio:", e);
                updatePlayButtonState(audioKey, false);
                currentAudio = null;
                currentPlayingAudioKey = null;
                URL.revokeObjectURL(audioUrl);
            });

            updatePlayButtonState(audioKey, true);

            currentAudio.onended = () => {
                updatePlayButtonState(audioKey, false);
                currentAudio = null;
                currentPlayingAudioKey = null;
                URL.revokeObjectURL(audioUrl);
            };
        }
    }

    function addPlayButton(audioKey, isLoading = false) {
        const playButtonWrapper = document.createElement("div");
        playButtonWrapper.className = "play-button-wrapper";
        playButtonWrapper.dataset.audioKey = audioKey;
        playButtonWrapper.onclick = () => playAudio(audioKey);

        if (isLoading) {
            playButtonWrapper.innerHTML = `
                <div class="loading-spinner"></div>
                <span class="play-button-text">음성 파일을 생성 중입니다...</span>
            `;
        } else {
            playButtonWrapper.innerHTML = `
                <button class="play-button" title="음성 재생">
                    <svg width="20" height="20" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>
                </button>
                <span class="play-button-text">음성으로 듣기</span>
            `;
        }
        return playButtonWrapper;
    }

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
        msgContainer.innerHTML = '';

        if (sender === 'bot' && text.includes("Daily Plan") && text.includes("Meal Plan")) {
            const parts = text.split("Meal Plan");
            const workoutPlanPart = parts[0];
            const mealPlanPart = "Meal Plan" + parts[1];

            const workoutPlanNode = document.createElement("div");
            workoutPlanNode.innerHTML = workoutPlanPart.replace(/\n/g, '<br>');
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
                if (!chatBox) return;
                chatBox.innerHTML = '';
                chatHistory.forEach(async msg => {
                    const msgContainer = document.createElement("div");
                    msgContainer.className = `message ${msg.sender}`;
                    chatBox.appendChild(msgContainer);

                    if (msg.sender === 'bot' && msg.audioKey) {
                        const audioBlob = await getAudio(msg.audioKey);
                        if (audioBlob) {
                            const playButtonWrapper = addPlayButton(msg.audioKey, false);
                            msgContainer.parentNode.insertBefore(playButtonWrapper, msgContainer);
                        }
                    }
                    appendMessage(msg.sender, msg.text, msg.videos || [], msgContainer);
                });
                if (mainContent) mainContent.classList.add("chat-active");
                chatBox.scrollTop = chatBox.scrollHeight;
            } catch (e) {
                console.error("Failed to parse chat history from sessionStorage:", e);
                sessionStorage.removeItem("chatHistory");
                chatHistory = [];
            }
        }
    }

    function clearImagePreview() {
        if(imageInput) imageInput.value = "";
        if(previewImage) previewImage.src = "";
        if(previewWrapper) previewWrapper.classList.add("hidden");
    }

    if(clearImageBtn) clearImageBtn.addEventListener("click", clearImagePreview);

    if(imageInput) imageInput.addEventListener("change", () => {
        const file = imageInput.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = () => {
                previewImage.src = reader.result;
                previewWrapper.classList.remove("hidden");
            };
            reader.readAsDataURL(file);
        } else {
            clearImagePreview();
        }
    });

    if(chatForm) chatForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const message = userInput.value.trim();
        const file = imageInput.files[0];
        if (!message && !file) return;

        if (welcomeMessage && !mainContent.classList.contains("chat-active")) {
            mainContent.classList.add("chat-active");
        }

        appendMessage("user", message || "[이미지 전송]");
        chatHistory.push({ sender: "user", text: message || "[이미지 전송]", videos: [] });
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

        const ttsLoadingWrapper = addPlayButton(null, true);
        botMessageDiv.parentNode.insertBefore(ttsLoadingWrapper, botMessageDiv);

        let fullStreamBuffer = "";
        let youtubeVideos = [];

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
                
                try {
                    const youtubeSearchRes = await fetch(`${BASE_API_URL}/youtube_search?query=${encodeURIComponent(fullStreamBuffer)}`, {
                        headers: { Authorization: `Bearer ${token}` },
                    });
                    if (youtubeSearchRes.ok) {
                        const videoData = await youtubeSearchRes.json();
                        if (videoData && videoData.length > 0) {
                            youtubeVideos = videoData;
                        }
                    } else {
                        console.error("Failed to fetch YouTube videos:", youtubeSearchRes.status, youtubeSearchRes.statusText);
                    }
                } catch (youtubeErr) {
                    console.error("Error fetching YouTube videos:", youtubeErr);
                }

                try {
                    const ttsRes = await fetch(`${BASE_API_URL}/batch_tts`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                        body: JSON.stringify({ text: fullStreamBuffer }),
                    });

                    if (ttsRes.ok) {
                        const audioBlob = await ttsRes.blob();
                        const audioKey = `tts-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
                        await addAudio(audioKey, audioBlob);
                        
                        const newPlayButtonWrapper = addPlayButton(audioKey, false);
                        ttsLoadingWrapper.replaceWith(newPlayButtonWrapper);

                        appendMessage("bot", fullStreamBuffer, youtubeVideos, botMessageDiv);
                        chatHistory.push({ sender: "bot", text: fullStreamBuffer, videos: youtubeVideos, audioKey: audioKey });
                    } else {
                        console.error("Failed to fetch TTS audio:", ttsRes.status, ttsRes.statusText);
                        ttsLoadingWrapper.remove();
                        appendMessage("bot", fullStreamBuffer, youtubeVideos, botMessageDiv);
                        chatHistory.push({ sender: "bot", text: fullStreamBuffer, videos: youtubeVideos });
                    }
                } catch (ttsErr) {
                    console.error("Error fetching TTS audio:", ttsErr);
                    ttsLoadingWrapper.remove();
                    appendMessage("bot", fullStreamBuffer, youtubeVideos, botMessageDiv);
                    chatHistory.push({ sender: "bot", text: fullStreamBuffer, videos: youtubeVideos });
                }
                saveChatHistory();
            } else {
                botMessageDiv.innerText = "❗ 오류가 발생했습니다.";
                ttsLoadingWrapper.remove();
                chatHistory.push({ sender: "bot", text: "❗ 오류가 발생했습니다." });
                saveChatHistory();
            }
        } catch (err) {
            botMessageDiv.innerText = "❗ 네트워크 오류입니다.";
            ttsLoadingWrapper.remove();
            chatHistory.push({ sender: "bot", text: "❗ 네트워크 오류입니다." });
            saveChatHistory();
            console.error(err);
        }
        clearImagePreview();
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

    if(closeModalBtn) closeModalBtn.addEventListener("click", () => modal.classList.add("hidden"));
    window.addEventListener("click", (e) => {
        if (e.target === modal) modal.classList.add("hidden");
    });

    // 페이지 로드 시 채팅 기록 불러오기
    loadChatHistory();
  }

  // --- 내 정보 페이지 (profile.html) 전용 로직 ---
  if (window.location.pathname.endsWith("profile.html")) {
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
        set("profile-level", user.level_desc ? `Lv.${user.level} ${user.level_desc}` : user.level);
        set("profile-injury-detail", user.injury_part || "없음");
      })
      .catch(err => {
        alert("내 정보를 불러오는 데 실패했습니다.");
        console.error(err);
        // window.location.href = "index.html"; // 에러 발생 시 강제 로그아웃 대신 콘솔에만 출력
      });
  }
});