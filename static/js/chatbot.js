
(function () {
    const launcher = document.getElementById("cpChatLauncher");
    const panel = document.getElementById("cpChatPanel");
    const closeButton = document.getElementById("cpChatClose");
    const form = document.getElementById("cpChatForm");
    const input = document.getElementById("cpChatInput");
    const messages = document.getElementById("cpChatMessages");
    const sendButton = document.getElementById("cpChatSend");

    if (!launcher || !panel || !form || !input || !messages) {
        return;
    }

    function addMessage(text, type) {
        const bubble = document.createElement("div");
        bubble.className = "cp-chat-message " +
            (type === "user" ? "cp-chat-user" : "cp-chat-bot");

        // textContent prevents user text from being interpreted as HTML.
        bubble.textContent = text;
        messages.appendChild(bubble);
        messages.scrollTop = messages.scrollHeight;
        return bubble;
    }

    function openChat() {
        panel.classList.add("cp-open");
        panel.setAttribute("aria-hidden", "false");
        launcher.setAttribute("aria-expanded", "true");
        input.focus();

        if (!messages.dataset.greeted) {
            addMessage(
                "Namaste! 👋 Ask me about complaints, tracking, " +
                "categories, priority or login. / Apni complaint " +
                "ke baare mein poochhein.",
                "bot"
            );
            messages.dataset.greeted = "true";
        }
    }

    function closeChat() {
        panel.classList.remove("cp-open");
        panel.setAttribute("aria-hidden", "true");
        launcher.setAttribute("aria-expanded", "false");
        launcher.focus();
    }

    launcher.addEventListener("click", function () {
        if (panel.classList.contains("cp-open")) {
            closeChat();
        } else {
            openChat();
        }
    });

    if (closeButton) {
        closeButton.addEventListener("click", closeChat);
    }

    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        const message = input.value.trim();

        if (!message) {
            return;
        }

        addMessage(message, "user");
        input.value = "";
        input.disabled = true;
        sendButton.disabled = true;

        const thinking = addMessage("Thinking... / Jawab taiyar ho raha hai...", "bot");

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ message: message })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Request failed.");
            }

            thinking.textContent = data.reply;
        } catch (error) {
            thinking.textContent =
                "Sorry, chat service is temporarily unavailable. " +
                "Please try again. / Kripya thodi der baad dobara try karein.";
        } finally {
            input.disabled = false;
            sendButton.disabled = false;
            input.focus();
            messages.scrollTop = messages.scrollHeight;
        }
    });
})();
