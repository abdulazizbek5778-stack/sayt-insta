document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('[data-history-back]')?.addEventListener('click', () => history.back());
    document.querySelector('[data-history-forward]')?.addEventListener('click', () => history.forward());

    const searchToggle = document.querySelector('.search-toggle');
    const searchPanel = document.getElementById('global-search-panel');
    const searchInput = document.getElementById('global-search-input');
    const searchResults = document.getElementById('global-search-results');
    let searchTimer = null;
    let searchRequest = null;

    function toggleSearchPanel(forceOpen = null) {
        if (!searchToggle || !searchPanel || !searchInput) return;
        const shouldOpen = forceOpen === null ? !searchPanel.classList.contains('is-open') : forceOpen;
        searchPanel.classList.toggle('is-open', shouldOpen);
        searchToggle.setAttribute('aria-expanded', String(shouldOpen));
        if (shouldOpen) {
            setTimeout(() => searchInput.focus(), 80);
        } else {
            searchRequest?.abort();
            searchInput.value = '';
            if (searchResults) {
                searchResults.innerHTML = '';
                searchResults.classList.remove('is-visible');
            }
        }
    }

    function renderSearchResults(items) {
        if (!searchResults) return;
        searchResults.replaceChildren();
        if (!items.length) {
            const empty = document.createElement('div');
            empty.className = 'search-empty';
            empty.textContent = 'Hech narsa topilmadi';
            searchResults.append(empty);
            searchResults.classList.add('is-visible');
            return;
        }

        items.forEach((item) => {
            const link = document.createElement('a');
            link.className = 'search-result-item';
            link.href = item.url;
            const title = document.createElement('span');
            title.className = 'search-result-title';
            title.textContent = item.title;
            const meta = document.createElement('span');
            meta.className = 'search-result-meta';
            meta.textContent = item.meta;
            link.append(title, meta);
            searchResults.append(link);
        });
        searchResults.classList.add('is-visible');
    }

    async function performSearch() {
        if (!searchInput || !searchResults || !searchPanel) return;
        const query = searchInput.value.trim().toLowerCase();
        if (!query) {
            searchRequest?.abort();
            searchResults.replaceChildren();
            searchResults.classList.remove('is-visible');
            return;
        }
        searchRequest?.abort();
        searchRequest = new AbortController();
        const requestQuery = query;
        try {
            const url = new URL(searchPanel.dataset.searchUrl, window.location.origin);
            url.searchParams.set('q', query);
            const response = await fetch(url, { signal: searchRequest.signal });
            if (!response.ok) throw new Error('Qidiruv natijalarini yuklab bo‘lmadi.');
            const data = await response.json();
            if (searchInput.value.trim().toLowerCase() === requestQuery) {
                renderSearchResults(data.results);
            }
        } catch (error) {
            if (error.name === 'AbortError') return;
            const status = document.createElement('div');
            status.className = 'search-empty';
            status.textContent = error.message || 'Qidiruvda xatolik yuz berdi.';
            searchResults.replaceChildren(status);
            searchResults.classList.add('is-visible');
        }
    }

    if (searchToggle && searchPanel && searchInput && searchResults) {
        searchToggle.addEventListener('click', () => toggleSearchPanel());
        searchInput.addEventListener('input', () => {
            window.clearTimeout(searchTimer);
            searchTimer = window.setTimeout(performSearch, 300);
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                toggleSearchPanel(false);
            }
        });
        searchResults.addEventListener('click', () => toggleSearchPanel(false));
        document.addEventListener('click', (event) => {
            const clickedInsideSearch = searchPanel.contains(event.target) || searchToggle.contains(event.target);
            if (!clickedInsideSearch) {
                toggleSearchPanel(false);
            }
        });
    }

    const storyInput = document.getElementById('story-upload-input');
    const storyPreviewWrap = document.querySelector('[data-story-preview]');
    const storyPreviewMedia = document.querySelector('[data-story-preview-media]');
    const storyFileName = document.querySelector('[data-story-file-name]');

    if (storyInput && storyPreviewWrap && storyPreviewMedia) {
        storyInput.addEventListener('change', () => {
            const file = storyInput.files && storyInput.files[0];
            if (!file) {
                storyPreviewWrap.hidden = true;
                storyPreviewMedia.innerHTML = '';
                if (storyFileName) storyFileName.textContent = 'Rasm yoki video tanlang';
                return;
            }

            const objectUrl = URL.createObjectURL(file);
            const mediaEl = file.type.startsWith('video/') ? document.createElement('video') : document.createElement('img');
            mediaEl.src = objectUrl;
            if (mediaEl.tagName === 'VIDEO') {
                mediaEl.muted = true;
                mediaEl.playsInline = true;
                mediaEl.autoplay = true;
                mediaEl.loop = true;
            }
            storyPreviewMedia.innerHTML = '';
            storyPreviewMedia.appendChild(mediaEl);
            storyPreviewWrap.hidden = false;
            if (storyFileName) storyFileName.textContent = file.name;
        });
    }

    const chatPanel = document.getElementById('community-chat');
    const chatContacts = document.getElementById('chat-contacts');
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-composer');
    const chatInput = document.getElementById('chat-input');
    const chatPersonName = document.getElementById('chat-person-name');
    const chatPersonStatus = document.getElementById('chat-person-status');
    const chatPersonAvatar = document.getElementById('chat-person-avatar');
    const chatStatus = document.getElementById('chat-status');

    if (chatPanel && chatContacts && chatMessages && chatForm && chatInput) {
        const contactsUrl = chatPanel.dataset.contactsUrl;
        const messageUrlTemplate = chatPanel.dataset.messageUrlTemplate;
        const currentUserId = Number(chatPanel.dataset.currentUserId);
        let contacts = [];
        let activeContactId = null;
        let lastMessageId = 0;
        const renderedMessageIds = new Set();
        let contactsRequestPending = false;
        let messagesRequestPending = false;
        let searchQuery = '';
        const searchInputEl = document.getElementById('chat-contacts-search');
        const urlParams = new URLSearchParams(window.location.search);
        const preselectedUserId = Number(urlParams.get('user'));

        function messageUrl(userId) {
            return messageUrlTemplate.replace('/0/', `/${userId}/`);
        }

        function setChatStatus(text) {
            chatStatus.textContent = text;
        }

        function appendMessage(message) {
            if (renderedMessageIds.has(message.id)) return;
            renderedMessageIds.add(message.id);
            const row = document.createElement('div');
            row.className = `chat-message ${message.sender_id === currentUserId ? 'outgoing' : 'incoming'}`;
            const body = document.createElement('span');
            body.textContent = message.body;
            const time = document.createElement('time');
            time.dateTime = message.created_at;
            time.textContent = new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            row.append(body, time);
            chatMessages.append(row);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        async function loadMessages(initial = false) {
            if (!activeContactId || messagesRequestPending) return;
            messagesRequestPending = true;
            try {
                const url = new URL(messageUrl(activeContactId), window.location.origin);
                if (!initial && lastMessageId) url.searchParams.set('after', String(lastMessageId));
                const response = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                if (!response.ok) throw new Error('Xabarlarni yuklab bo‘lmadi.');
                const data = await response.json();
                if (Number(activeContactId) !== Number(url.pathname.match(/\/(\d+)\/messages\/$/)?.[1])) return;
                if (initial) {
                    chatMessages.replaceChildren();
                    renderedMessageIds.clear();
                }
                data.messages.forEach((message) => {
                    appendMessage(message);
                    lastMessageId = Math.max(lastMessageId, message.id);
                });
                if (initial && data.messages.length === 0) {
                    const empty = document.createElement('p');
                    empty.className = 'chat-list-status';
                    empty.textContent = 'Birinchi xabarni yuboring — suhbat shu yerda davom etadi.';
                    chatMessages.append(empty);
                }
                setChatStatus('');
            } catch (error) {
                setChatStatus(error.message || 'Ulanishda xatolik. Qayta urinib ko‘ring.');
            } finally {
                messagesRequestPending = false;
            }
        }

        function selectContact(contact) {
            activeContactId = contact.id;
            lastMessageId = 0;
            chatContacts.querySelectorAll('.chat-contact').forEach((item) => {
                item.classList.toggle('is-active', Number(item.dataset.userId) === contact.id);
            });
            chatPersonName.textContent = contact.name;
            chatPersonStatus.textContent = contact.is_online ? 'Onlayn hozir' : 'Hozir oflayn';
            chatPersonStatus.classList.toggle('is-offline', !contact.is_online);
            chatPersonAvatar.replaceChildren();
            if (contact.avatar_url) {
                const image = document.createElement('img');
                image.className = 'chat-avatar-image';
                image.src = contact.avatar_url;
                image.alt = '';
                chatPersonAvatar.append(image);
            } else {
                chatPersonAvatar.textContent = contact.name.charAt(0).toUpperCase();
            }
            chatPersonAvatar.classList.toggle('has-avatar', Boolean(contact.avatar_url));
            chatInput.disabled = false;
            chatForm.querySelector('button[type="submit"]').disabled = false;
            chatMessages.replaceChildren();
            const loading = document.createElement('p');
            loading.className = 'chat-list-status';
            loading.textContent = 'Xabarlar yuklanmoqda...';
            chatMessages.append(loading);
            loadMessages(true);
        }

        function renderContacts() {
            chatContacts.replaceChildren();
            const filtered = searchQuery
                ? contacts.filter(c => (c.name || '').toLowerCase().includes(searchQuery) || (c.username || '').toLowerCase().includes(searchQuery))
                : contacts;

            if (filtered.length === 0) {
                const empty = document.createElement('li');
                empty.className = 'chat-list-status';
                empty.textContent = searchQuery ? 'Foydalanuvchi topilmadi.' : 'Hozircha boshqa foydalanuvchi yo‘q.';
                chatContacts.append(empty);
                return;
            }

            filtered.forEach((contact) => {
                const item = document.createElement('li');
                item.className = `chat-contact${contact.id === activeContactId ? ' is-active' : ''}`;
                item.dataset.userId = String(contact.id);
                item.tabIndex = 0;
                item.setAttribute('role', 'button');
                item.setAttribute('aria-label', `Chat: ${contact.name}`);
                const avatar = document.createElement('div');
                avatar.className = `chat-contact-avatar${contact.avatar_url ? ' has-avatar' : ''}`;
                if (contact.avatar_url) {
                    const image = document.createElement('img');
                    image.className = 'chat-avatar-image';
                    image.src = contact.avatar_url;
                    image.alt = '';
                    avatar.append(image);
                } else {
                    avatar.textContent = contact.name.charAt(0).toUpperCase();
                }
                const meta = document.createElement('div');
                meta.className = 'chat-contact-meta';
                const topline = document.createElement('div');
                topline.className = 'chat-contact-topline';
                const name = document.createElement('strong');
                name.textContent = contact.name;
                const online = document.createElement('span');
                online.className = `chat-online-dot${contact.is_online ? ' is-online' : ''}`;
                online.setAttribute('aria-label', contact.is_online ? 'Onlayn' : 'Oflayn');
                topline.append(name, online);
                const username = document.createElement('small');
                username.textContent = `@${contact.username}`;
                meta.append(topline, username);
                item.append(avatar, meta);
                item.addEventListener('click', () => selectContact(contact));
                item.addEventListener('keydown', (event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        selectContact(contact);
                    }
                });
                chatContacts.append(item);
            });
        }

        async function refreshContacts() {
            if (contactsRequestPending) return;
            contactsRequestPending = true;
            try {
                const response = await fetch(contactsUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                if (!response.ok) throw new Error('Foydalanuvchilarni yuklab bo‘lmadi.');
                const data = await response.json();
                contacts = data.contacts;
                renderContacts();
                const activeContact = contacts.find((contact) => contact.id === activeContactId);
                if (activeContact) {
                    chatPersonStatus.textContent = activeContact.is_online ? 'Onlayn hozir' : 'Hozir oflayn';
                    chatPersonStatus.classList.toggle('is-offline', !activeContact.is_online);
                } else if (!activeContactId && preselectedUserId) {
                    const target = contacts.find(c => c.id === preselectedUserId);
                    if (target) {
                        selectContact(target);
                    } else if (contacts.length) {
                        selectContact(contacts[0]);
                    }
                } else if (!activeContactId && contacts.length) {
                    selectContact(contacts[0]);
                }

                const floatingBadge = document.getElementById('floating-chat-badge');
                if (floatingBadge) {
                    const onlineCount = contacts.filter(c => c.is_online).length;
                    if (onlineCount > 0) {
                        floatingBadge.textContent = String(onlineCount);
                        floatingBadge.style.display = 'inline-flex';
                    }
                }
            } catch (error) {
                setChatStatus(error.message || 'Foydalanuvchilarni yuklab bo‘lmadi.');
            } finally {
                contactsRequestPending = false;
            }
        }

        if (searchInputEl) {
            searchInputEl.addEventListener('input', (e) => {
                searchQuery = e.target.value.trim().toLowerCase();
                renderContacts();
            });
        }

        document.querySelectorAll('.quick-emoji-pill').forEach(btn => {
            btn.addEventListener('click', () => {
                if (chatInput.disabled) return;
                const emoji = btn.dataset.emoji;
                chatInput.value += (chatInput.value ? ' ' : '') + emoji;
                chatInput.focus();
            });
        });

        chatForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const body = chatInput.value.trim();
            if (!body || !activeContactId) return;
            const submitButton = chatForm.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            try {
                const response = await fetch(messageUrl(activeContactId), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': chatForm.querySelector('[name="csrfmiddlewaretoken"]').value,
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({ body }),
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Xabar yuborilmadi.');
                chatInput.value = '';
                appendMessage(data.message);
                lastMessageId = Math.max(lastMessageId, data.message.id);
                setChatStatus('');
            } catch (error) {
                setChatStatus(error.message || 'Xabar yuborilmadi. Qayta urinib ko‘ring.');
            } finally {
                submitButton.disabled = false;
                chatInput.focus();
            }
        });

        refreshContacts();
        window.setInterval(refreshContacts, 20000);
        window.setInterval(() => loadMessages(), 2500);
    }

    const avatarInput = document.querySelector('input[name="avatar"]');
    const avatarPreview = document.querySelector('[data-avatar-preview]');

    if (avatarInput && avatarPreview) {
        avatarInput.addEventListener('change', () => {
            const [file] = avatarInput.files;
            if (!file) return;
            avatarPreview.src = URL.createObjectURL(file);
        });
    }

    // Avatar Lightbox View
    const profileAvatar = document.querySelector('.profile-avatar');
    if (profileAvatar) {
        profileAvatar.title = "Rasmni to'liq ko'rish uchun bosing";
        profileAvatar.addEventListener('click', () => {
            const overlay = document.createElement('div');
            overlay.className = 'avatar-lightbox-overlay';
            overlay.innerHTML = `
                <div class="avatar-lightbox-card">
                    <button class="avatar-lightbox-close" aria-label="Yopish">✕</button>
                    <img src="${profileAvatar.src}" alt="${profileAvatar.alt}">
                    <div class="avatar-lightbox-caption">
                        <strong>xurramov.abdulaziz</strong>
                        <span>Amir Temur haykali oldida ✨</span>
                    </div>
                </div>
            `;
            const close = () => {
                overlay.classList.add('is-closing');
                setTimeout(() => overlay.remove(), 250);
            };
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay || e.target.classList.contains('avatar-lightbox-close')) {
                    close();
                }
            });
            document.body.appendChild(overlay);
            requestAnimationFrame(() => overlay.classList.add('is-open'));
        });
    }

    // ─── Floating Leaves ("Takoy Suzib Yuruvchi Barglar") Simulation ───
    const canvas = document.createElement('canvas');
    canvas.id = 'leaves-canvas';
    canvas.style.cssText = `
        position: fixed;
        inset: 0;
        width: 100vw;
        height: 100vh;
        pointer-events: none;
        z-index: 60;
    `;
    document.body.prepend(canvas);

    const ctx = canvas.getContext('2d');
    let W = canvas.width = window.innerWidth;
    let H = canvas.height = window.innerHeight;

    // Palette of rich autumn and fresh leaf colors
    const LEAF_PALETTES = [
        {
            name: 'autumn-gold',
            frontGrad: ['#fbbf24', '#d97706', '#92400e'],
            backGrad: ['#fde68a', '#d97706'],
            vein: 'rgba(120, 53, 15, 0.45)',
            glow: 'rgba(251, 191, 36, 0.25)',
        },
        {
            name: 'emerald',
            frontGrad: ['#34d399', '#059669', '#065f46'],
            backGrad: ['#a7f3d0', '#059669'],
            vein: 'rgba(4, 120, 87, 0.45)',
            glow: 'rgba(16, 185, 129, 0.25)',
        },
        {
            name: 'scarlet-crimson',
            frontGrad: ['#f87171', '#dc2626', '#7f1d1d'],
            backGrad: ['#fecaca', '#b91c1c'],
            vein: 'rgba(153, 27, 27, 0.5)',
            glow: 'rgba(239, 68, 68, 0.25)',
        },
        {
            name: 'warm-copper',
            frontGrad: ['#fb923c', '#ea580c', '#9a3412'],
            backGrad: ['#fed7aa', '#c2410c'],
            vein: 'rgba(154, 52, 18, 0.5)',
            glow: 'rgba(249, 115, 22, 0.25)',
        },
        {
            name: 'olive-lime',
            frontGrad: ['#a3e635', '#65a30d', '#3f6212'],
            backGrad: ['#d9f99d', '#65a30d'],
            vein: 'rgba(63, 98, 18, 0.45)',
            glow: 'rgba(132, 204, 22, 0.25)',
        },
    ];

    const mouse = { x: W / 2, y: H / 2, prevX: W / 2, prevY: H / 2, vx: 0, vy: 0 };
    let lastMouseMove = Date.now();

    window.addEventListener('mousemove', e => {
        mouse.vx = (e.clientX - mouse.prevX) * 0.2;
        mouse.vy = (e.clientY - mouse.prevY) * 0.2;
        mouse.prevX = mouse.x;
        mouse.prevY = mouse.y;
        mouse.x = e.clientX;
        mouse.y = e.clientY;
        lastMouseMove = Date.now();
    });

    // Wind gust on click
    window.addEventListener('click', e => {
        createWindBurst(e.clientX, e.clientY, 120);
    });

    class FloatingLeaf {
        constructor() {
            this.reset(true);
        }

        reset(initial = false) {
            this.palette = LEAF_PALETTES[Math.floor(Math.random() * LEAF_PALETTES.length)];
            this.leafType = Math.floor(Math.random() * 4); // 0: birch/pointed, 1: maple, 2: willow, 3: oval
            
            // Size & depth layers (foreground / midground / background)
            this.depth = 0.35 + Math.random() * 0.65; // 0.35 to 1.0
            this.size = (18 + Math.random() * 24) * this.depth;
            
            // Positioning: spread across screen or enter from top / top-left
            this.x = initial ? Math.random() * (W + 200) - 100 : Math.random() * (W + 300) - 200;
            this.y = initial ? Math.random() * H : -this.size * 2 - Math.random() * 80;

            // Velocities
            this.baseVy = (0.55 + Math.random() * 0.75) * this.depth;
            this.vy = this.baseVy;
            this.vx = (0.25 + Math.random() * 0.6) * this.depth;

            // 3D Angles
            this.yaw = Math.random() * Math.PI * 2;         // 2D steering rotation
            this.yawSpeed = (Math.random() - 0.5) * 0.015;
            this.roll = Math.random() * Math.PI * 2;        // 3D flip rotation (scaleX)
            this.rollSpeed = 0.015 + Math.random() * 0.025;
            this.pitch = Math.random() * Math.PI * 2;       // 3D tilt (scaleY)
            this.pitchSpeed = 0.01 + Math.random() * 0.02;

            // Swaying sinusoidal floating motion
            this.swayAngle = Math.random() * Math.PI * 2;
            this.swayRate = 0.018 + Math.random() * 0.022;
            this.swayAmp = (1.2 + Math.random() * 2.2) * this.depth;

            this.opacity = (0.7 + Math.random() * 0.3) * (0.6 + this.depth * 0.4);
            this.wobble = Math.random() * 10;
        }

        update(globalWind) {
            this.swayAngle += this.swayRate;
            this.roll += this.rollSpeed;
            this.pitch += this.pitchSpeed;
            this.yaw += this.yawSpeed + Math.sin(this.swayAngle) * 0.008;

            // Lift and air resistance: flatter leaf falls slower and glides more sideways
            const cosRoll = Math.cos(this.roll);
            const flatness = Math.abs(cosRoll); // 1 = fully flat, 0 = vertical edge-on
            const glideFactor = 0.6 + flatness * 0.7;

            // Swaying side drift
            const swayForce = Math.sin(this.swayAngle) * this.swayAmp;
            this.x += this.vx * glideFactor + swayForce + globalWind;
            this.y += this.vy * (1.2 - flatness * 0.45);

            // Mouse wind interaction
            const dx = this.x - mouse.x;
            const dy = this.y - mouse.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const mouseActive = (Date.now() - lastMouseMove) < 1000;
            
            if (dist < 160 && mouseActive) {
                const force = (160 - dist) / 160;
                this.x += (dx / dist) * force * 5 + mouse.vx * force * 1.5;
                this.y += (dy / dist) * force * 3 + mouse.vy * force * 1.5;
                this.rollSpeed += force * 0.04;
                this.yawSpeed += (Math.random() - 0.5) * 0.03;
            }

            // Damping speeds back to normal
            this.rollSpeed += (0.02 - this.rollSpeed) * 0.02;

            // Screen boundaries wrap around smoothly
            if (this.y > H + this.size * 2) {
                this.reset(false);
            }
            if (this.x < -this.size * 2) {
                this.x = W + this.size;
            } else if (this.x > W + this.size * 2) {
                this.x = -this.size;
            }
        }

        draw() {
            ctx.save();
            ctx.translate(this.x, this.y);

            // 3D rotation projection:
            // yaw = in-plane rotation
            // roll = horizontal flip (cross 0 creates front/back flip!)
            // pitch = vertical foreshortening
            ctx.rotate(this.yaw);
            
            const cosRoll = Math.cos(this.roll);
            const isFront = cosRoll >= 0;
            const scaleX = cosRoll;
            const scaleY = Math.sin(this.pitch) * 0.25 + 0.75;
            
            ctx.scale(scaleX, scaleY);
            ctx.globalAlpha = this.opacity;

            // Draw shadow for foreground leaves
            if (this.depth > 0.65) {
                ctx.shadowColor = 'rgba(0, 0, 0, 0.35)';
                ctx.shadowBlur = 8 * this.depth;
                ctx.shadowOffsetX = 3;
                ctx.shadowOffsetY = 6;
            }

            const s = this.size;
            const pal = this.palette;

            // Gradient selection (front face has richer gradient, back face is lighter/softer)
            const gradColors = isFront ? pal.frontGrad : pal.backGrad;
            const grad = ctx.createLinearGradient(0, -s, 0, s);
            grad.addColorStop(0, gradColors[0]);
            grad.addColorStop(0.5, gradColors[1]);
            if (gradColors[2]) grad.addColorStop(1, gradColors[2]);

            // ─── Leaf Geometry Based on Type ───
            ctx.beginPath();

            if (this.leafType === 0) {
                // Pointed Linden / Birch leaf
                ctx.moveTo(0, s * 0.5); // stem base
                ctx.lineTo(0, s * 0.3); // stem connection
                // Right lobe
                ctx.bezierCurveTo(s * 0.45, s * 0.2, s * 0.42, -s * 0.4, 0, -s * 0.65);
                // Left lobe
                ctx.bezierCurveTo(-s * 0.42, -s * 0.4, -s * 0.45, s * 0.2, 0, s * 0.3);
            } else if (this.leafType === 1) {
                // Autumn Maple / Lobed Leaf (chinor bargi)
                ctx.moveTo(0, s * 0.5);
                ctx.lineTo(0, s * 0.28);
                // Right lower lobe
                ctx.quadraticCurveTo(s * 0.4, s * 0.2, s * 0.45, 0.05);
                ctx.lineTo(s * 0.32, -0.05);
                // Right upper lobe
                ctx.quadraticCurveTo(s * 0.5, -s * 0.25, s * 0.35, -s * 0.45);
                ctx.lineTo(s * 0.2, -s * 0.42);
                // Central tip
                ctx.quadraticCurveTo(s * 0.15, -s * 0.6, 0, -s * 0.72);
                // Left upper lobe
                ctx.quadraticCurveTo(-s * 0.15, -s * 0.6, -s * 0.2, -s * 0.42);
                ctx.lineTo(-s * 0.35, -s * 0.45);
                // Left lower lobe
                ctx.quadraticCurveTo(-s * 0.5, -s * 0.25, -s * 0.32, -0.05);
                ctx.lineTo(-s * 0.45, 0.05);
                ctx.quadraticCurveTo(-s * 0.4, s * 0.2, 0, s * 0.28);
            } else if (this.leafType === 2) {
                // Slender Willow leaf (majnuntol bargi)
                ctx.moveTo(0, s * 0.55);
                ctx.lineTo(0, s * 0.38);
                ctx.bezierCurveTo(s * 0.2, s * 0.15, s * 0.18, -s * 0.45, 0, -s * 0.75);
                ctx.bezierCurveTo(-s * 0.18, -s * 0.45, -s * 0.2, s * 0.15, 0, s * 0.38);
            } else {
                // Soft organic teardrop leaf
                ctx.moveTo(0, s * 0.48);
                ctx.lineTo(0, s * 0.26);
                ctx.bezierCurveTo(s * 0.38, s * 0.12, s * 0.35, -s * 0.35, 0, -s * 0.62);
                ctx.bezierCurveTo(-s * 0.35, -s * 0.35, -s * 0.38, s * 0.12, 0, s * 0.26);
            }

            ctx.closePath();
            ctx.fillStyle = grad;
            ctx.fill();

            // Subtle stem stroke
            ctx.beginPath();
            ctx.moveTo(0, s * 0.5);
            ctx.lineTo(0, s * 0.25);
            ctx.strokeStyle = isFront ? pal.vein : 'rgba(100, 100, 100, 0.3)';
            ctx.lineWidth = 1.2;
            ctx.stroke();

            // Central leaf rib / vein
            ctx.beginPath();
            ctx.moveTo(0, s * 0.26);
            ctx.quadraticCurveTo(0, -s * 0.15, 0, -s * 0.58);
            ctx.strokeStyle = isFront ? pal.vein : 'rgba(255, 255, 255, 0.22)';
            ctx.lineWidth = Math.max(0.7, 1.3 * (s / 30));
            ctx.stroke();

            // Side lateral veins (organic ribs)
            const veinPairs = this.leafType === 2 ? 4 : 3;
            ctx.lineWidth = 0.6;
            ctx.strokeStyle = isFront ? pal.vein : 'rgba(255, 255, 255, 0.15)';
            for (let i = 1; i <= veinPairs; i++) {
                const vy = s * 0.2 - (i * (s * 0.65 / (veinPairs + 1)));
                const spread = (s * 0.22) * (1 - (i / (veinPairs + 1.2)));
                // Right rib
                ctx.beginPath();
                ctx.moveTo(0, vy);
                ctx.quadraticCurveTo(spread * 0.6, vy - s * 0.05, spread, vy - s * 0.1);
                ctx.stroke();
                // Left rib
                ctx.beginPath();
                ctx.moveTo(0, vy);
                ctx.quadraticCurveTo(-spread * 0.6, vy - s * 0.05, -spread, vy - s * 0.1);
                ctx.stroke();
            }

            // Specular sheen / sun glint highlight on front face
            if (isFront && this.depth > 0.5) {
                const sheenGrad = ctx.createLinearGradient(-s * 0.2, -s * 0.3, s * 0.2, s * 0.1);
                sheenGrad.addColorStop(0, 'rgba(255, 255, 255, 0.28)');
                sheenGrad.addColorStop(0.5, 'rgba(255, 255, 255, 0.0)');
                sheenGrad.addColorStop(1, 'rgba(255, 255, 255, 0.0)');
                ctx.fillStyle = sheenGrad;
                ctx.fill();
            }

            ctx.restore();
        }
    }

    // Gentle luminous dust motes / glowing spores in the breeze
    class LuminousMote {
        constructor() {
            this.reset(true);
        }
        reset(initial = false) {
            this.x = Math.random() * W;
            this.y = initial ? Math.random() * H : H + 10;
            this.r = 0.8 + Math.random() * 1.6;
            this.vx = (Math.random() - 0.3) * 0.4;
            this.vy = -(0.2 + Math.random() * 0.4);
            this.alpha = 0;
            this.targetAlpha = 0.15 + Math.random() * 0.45;
            this.pulse = Math.random() * Math.PI * 2;
            this.pulseSpeed = 0.02 + Math.random() * 0.03;
            this.color = Math.random() > 0.5 ? '251, 191, 36' : '110, 231, 183';
        }
        update(wind) {
            this.x += this.vx + wind * 0.5;
            this.y += this.vy;
            this.pulse += this.pulseSpeed;
            if (this.alpha < this.targetAlpha) this.alpha = Math.min(this.alpha + 0.01, this.targetAlpha);
            if (this.y < -10 || this.x < -10 || this.x > W + 10) this.reset();
        }
        draw() {
            const glow = Math.sin(this.pulse) * 0.3 + 0.7;
            const a = this.alpha * glow;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.r * glow, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${this.color}, ${a})`;
            ctx.fill();
        }
    }

    // Number of leaves scaled to screen size (balanced for beauty and 60fps performance)
    const LEAF_COUNT = Math.max(16, Math.min(32, Math.floor(W / 45)));
    const leaves = Array.from({ length: LEAF_COUNT }, () => new FloatingLeaf());
    const motes = Array.from({ length: 30 }, () => new LuminousMote());

    function createWindBurst(cx, cy, radius) {
        leaves.forEach(leaf => {
            const dx = leaf.x - cx;
            const dy = leaf.y - cy;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < radius * 2) {
                const force = (radius * 2 - dist) / (radius * 2);
                leaf.vx += (dx / (dist || 1)) * force * 6;
                leaf.vy += (dy / (dist || 1)) * force * 4 - 2;
                leaf.rollSpeed += 0.08 * (Math.random() > 0.5 ? 1 : -1);
                leaf.yawSpeed += 0.05 * (Math.random() > 0.5 ? 1 : -1);
            }
        });
    }

    // Wind oscillation cycle (gentle breeze that shifts over time)
    let time = 0;
    function animate() {
        ctx.clearRect(0, 0, W, H);
        time += 0.015;

        // Ambient shifting wind
        const globalWind = Math.sin(time * 0.4) * 0.6 + 0.35;

        // Draw luminous atmospheric motes in background
        motes.forEach(m => {
            m.update(globalWind);
            m.draw();
        });

        // Update and draw floating leaves sorted by depth for realistic layering
        leaves.sort((a, b) => a.depth - b.depth);
        leaves.forEach(leaf => {
            leaf.update(globalWind);
            leaf.draw();
        });

        requestAnimationFrame(animate);
    }
    animate();

    window.addEventListener('resize', () => {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
    });

    // ─── Post Form Live Previews ─────────────────────────────
    const postImgInput = document.querySelector('input[name="img"]');
    const postImgBox = document.getElementById('img-preview-box');
    const postImgPreview = document.getElementById('img-preview');
    if (postImgInput && postImgBox && postImgPreview) {
        postImgInput.addEventListener('change', () => {
            const [file] = postImgInput.files;
            if (file) {
                postImgPreview.src = URL.createObjectURL(file);
                postImgBox.style.display = 'flex';
            } else {
                postImgBox.style.display = 'none';
            }
        });
    }

    const postVideoInput = document.querySelector('input[name="video"]');
    const postVideoBox = document.getElementById('video-preview-box');
    const postVideoPreview = document.getElementById('video-preview');
    if (postVideoInput && postVideoBox && postVideoPreview) {
        postVideoInput.addEventListener('change', () => {
            const [file] = postVideoInput.files;
            if (file) {
                postVideoPreview.src = URL.createObjectURL(file);
                postVideoBox.style.display = 'flex';
            } else {
                postVideoBox.style.display = 'none';
            }
        });
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    }

    // ─── Like Buttons ─────────────────────────────────────────
    document.querySelectorAll('.js-like-form').forEach(form => {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const button = form.querySelector('[data-post-like]');
            const countSpan = form.querySelector('.like-count');
            const isLikedBefore = button.classList.contains('is-liked');
            const formData = new FormData(form);

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: formData,
                });

                if (!response.ok) {
                    throw new Error('Like request failed');
                }

                const data = await response.json();
                button.classList.toggle('is-liked', data.liked);
                if (countSpan) {
                    const nextCount = Number(data.likes_count || 0);
                    countSpan.setAttribute('data-count', String(nextCount));
                    countSpan.textContent = nextCount > 0 ? `${nextCount}` : 'Yoqdi';
                }
            } catch (error) {
                button.classList.toggle('is-liked', isLikedBefore);
                console.error('Like failed', error);
            }
        });
    });

    document.querySelectorAll('.js-follow-form').forEach(form => {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const button = form.querySelector('button');
            const label = button.querySelector('span');
            const formData = new FormData(form);

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: formData,
                });

                if (!response.ok) {
                    throw new Error('Follow request failed');
                }

                const data = await response.json();
                button.classList.toggle('is-following', data.following);
                if (label) {
                    label.textContent = data.following ? 'Kuzatilmoqda' : 'Kuzatish';
                }
            } catch (error) {
                console.error('Follow failed', error);
            }
        });
    });

    // ─── Real-Time Post Comments Chat Manager ──────────────────
    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function updatePostCommentsBadge(postId, newCount) {
        const count = Math.max(0, Number(newCount) || 0);

        // Update post card stats row
        const postCard = document.getElementById(`post-${postId}`);
        if (postCard) {
            const statsSpans = postCard.querySelectorAll('.post-stats-row span');
            if (statsSpans.length >= 2) {
                statsSpans[1].textContent = `${count} ta izoh`;
            }
        }

        // Update action button label
        document.querySelectorAll(`[data-comments-label="${postId}"]`).forEach(el => {
            el.textContent = `Izohlar (${count})`;
        });

        // Update chat header pill
        document.querySelectorAll(`[data-comment-badge="${postId}"] .badge-num`).forEach(el => {
            el.textContent = count;
            el.dataset.count = count;
        });
    }

    const postChatMap = new Map();

    function initPostCommentsChats() {
        document.querySelectorAll('.post-comments-chat').forEach(chatEl => {
            const postId = Number(chatEl.dataset.postId);
            if (!postId) return;

            const stream = chatEl.querySelector('[data-comment-stream]');
            const currentUserId = Number(chatEl.dataset.currentUserId || 0);
            const postAuthorId = Number(chatEl.dataset.postAuthorId || 0);
            const renderedIds = new Set();

            let maxId = 0;
            if (stream) {
                stream.querySelectorAll('.comment-bubble').forEach(bubble => {
                    const cid = Number(bubble.dataset.commentId);
                    if (cid) {
                        renderedIds.add(cid);
                        maxId = Math.max(maxId, cid);
                    }
                });
                // Initial auto-scroll
                stream.scrollTop = stream.scrollHeight;
            }

            postChatMap.set(postId, {
                chatEl,
                stream,
                currentUserId,
                postAuthorId,
                renderedIds,
                lastCommentId: maxId,
                isPolling: false,
            });
        });
    }

    function createCommentBubbleNode(comment, currentUserId, postAuthorId) {
        const isOutgoing = Boolean(
            comment.is_current_user || (currentUserId && Number(comment.user_id) === Number(currentUserId))
        );
        const isAuthor = Boolean(
            comment.is_post_author || (postAuthorId && Number(comment.user_id) === Number(postAuthorId))
        );
        const canDelete = Boolean(comment.can_delete || isOutgoing || (postAuthorId && currentUserId === postAuthorId));

        const bubble = document.createElement('div');
        bubble.className = `comment-bubble ${isOutgoing ? 'is-outgoing' : 'is-incoming'}`;
        bubble.id = `comment-node-${comment.id}`;
        bubble.dataset.commentId = comment.id;

        const avatarInitial = (comment.username || 'A').charAt(0).toUpperCase();
        const avatarHtml = comment.avatar_url
            ? `<img src="${escapeHtml(comment.avatar_url)}" alt="${escapeHtml(comment.username)}" class="comment-user-avatar">`
            : `<div class="comment-avatar-letter">${escapeHtml(avatarInitial)}</div>`;

        const authorBadgeHtml = isAuthor ? '<span class="role-badge role-author">Muallif</span>' : '';
        const youBadgeHtml = isOutgoing ? '<span class="role-badge role-you">Siz</span>' : '';
        const deleteBtnHtml = canDelete
            ? `<button type="button" class="comment-del-btn js-delete-comment" data-delete-id="${comment.id}" title="Izohni o‘chirish" aria-label="Izohni o‘chirish">
                 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M3 6h18m-2 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path></svg>
               </button>`
            : '';

        bubble.innerHTML = `
            <div class="comment-avatar-slot">
                ${avatarHtml}
            </div>
            <div class="comment-bubble-body">
                <div class="comment-meta-bar">
                    <strong class="comment-username">${escapeHtml(comment.username)}</strong>
                    ${authorBadgeHtml}
                    ${youBadgeHtml}
                    <time class="comment-timestamp" datetime="${escapeHtml(comment.created_at || '')}">
                        ${escapeHtml(comment.created_time || 'Hozir')}
                    </time>
                    ${deleteBtnHtml}
                </div>
                <div class="comment-msg-content">${escapeHtml(comment.body)}</div>
            </div>
        `;

        return bubble;
    }

    async function pollCommentsForPost(state) {
        if (!state || state.isPolling) return;
        const chatEl = state.chatEl;
        const stream = state.stream;
        if (!chatEl || !stream) return;

        const commentsUrl = chatEl.dataset.commentsUrl;
        if (!commentsUrl) return;

        state.isPolling = true;
        try {
            const url = new URL(commentsUrl, window.location.origin);
            if (state.lastCommentId > 0) {
                url.searchParams.set('after', String(state.lastCommentId));
            }

            const response = await fetch(url.toString(), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            if (!response.ok) return;
            const data = await response.json();
            if (data.status !== 'ok' || !Array.isArray(data.comments)) return;

            const wasNearBottom = (stream.scrollHeight - stream.scrollTop - stream.clientHeight) < 60;
            let addedCount = 0;

            data.comments.forEach(c => {
                if (state.renderedIds.has(c.id)) return;
                state.renderedIds.add(c.id);
                state.lastCommentId = Math.max(state.lastCommentId, c.id);

                // Remove empty hint if present
                const emptyHint = chatEl.querySelector('[data-empty-hint]');
                if (emptyHint) emptyHint.remove();

                const node = createCommentBubbleNode(c, state.currentUserId, state.postAuthorId);
                stream.appendChild(node);
                addedCount++;
            });

            if (data.comments_count !== undefined) {
                updatePostCommentsBadge(Number(chatEl.dataset.postId), data.comments_count);
            }

            if (addedCount > 0 && wasNearBottom) {
                stream.scrollTo({ top: stream.scrollHeight, behavior: 'smooth' });
            }
        } catch (err) {
            // Silently ignore network hiccup during background polling
        } finally {
            state.isPolling = false;
        }
    }

    function pollAllCommentsChats() {
        postChatMap.forEach(state => {
            // Check if post chat is in viewport or visible
            const rect = state.chatEl.getBoundingClientRect();
            const isVisible = rect.top < window.innerHeight + 400 && rect.bottom > -400;
            if (isVisible) {
                pollCommentsForPost(state);
            }
        });
    }

    // Initialize all post chats
    initPostCommentsChats();

    // Start background real-time sync polling every 2.5 seconds
    setInterval(pollAllCommentsChats, 2500);

    // ─── Comment Form Submission ────────────────────────────────
    document.querySelectorAll('.js-comment-form').forEach(form => {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const input = form.querySelector('input[name="body"]');
            if (!input) return;
            const text = input.value.trim();
            if (!text) return;

            const postId = Number(form.dataset.postId);
            const state = postChatMap.get(postId);
            const submitBtn = form.querySelector('button[type="submit"]');

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.classList.add('is-sending');
            }

            const formData = new FormData(form);

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: formData,
                });

                if (!response.ok) {
                    throw new Error('Izoh yuborishda xatolik yuz berdi');
                }

                const data = await response.json();
                if (data.status === 'ok' && data.comment && state && state.stream) {
                    // Remove empty hint
                    const emptyHint = state.chatEl.querySelector('[data-empty-hint]');
                    if (emptyHint) emptyHint.remove();

                    if (!state.renderedIds.has(data.comment.id)) {
                        state.renderedIds.add(data.comment.id);
                        state.lastCommentId = Math.max(state.lastCommentId, data.comment.id);

                        const node = createCommentBubbleNode(data.comment, state.currentUserId, state.postAuthorId);
                        state.stream.appendChild(node);
                        state.stream.scrollTo({ top: state.stream.scrollHeight, behavior: 'smooth' });
                    }

                    if (data.comments_count !== undefined) {
                        updatePostCommentsBadge(postId, data.comments_count);
                    }
                }
                input.value = '';
                input.focus();
            } catch (error) {
                console.error('Comment submit error:', error);
                alert(error.message || 'Izoh yuborishda xatolik yuz berdi. Qayta urinib ko‘ring.');
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('is-sending');
                }
            }
        });
    });

    // ─── Comment Deletion ───────────────────────────────────────
    document.addEventListener('click', async (event) => {
        const delBtn = event.target.closest('.js-delete-comment');
        if (!delBtn) return;
        event.preventDefault();

        const commentId = Number(delBtn.dataset.deleteId);
        if (!commentId) return;

        if (!confirm('Haqiqatdan ham ushbu izohni o‘chirmoqchimisiz?')) return;

        const bubbleNode = document.getElementById(`comment-node-${commentId}`);
        const chatEl = delBtn.closest('.post-comments-chat');
        const postId = chatEl ? Number(chatEl.dataset.postId) : 0;
        const state = postChatMap.get(postId);

        try {
            delBtn.disabled = true;
            const response = await fetch(`/comment/${commentId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });

            if (!response.ok) throw new Error('Izohni o‘chirish imkoni bo‘lmadi');
            const data = await response.json();

            if (data.status === 'ok') {
                if (bubbleNode) {
                    bubbleNode.classList.add('is-deleting');
                    setTimeout(() => {
                        bubbleNode.remove();
                        if (state && state.renderedIds) {
                            state.renderedIds.delete(commentId);
                            // If stream is empty, show empty hint
                            if (state.stream && state.stream.querySelectorAll('.comment-bubble').length === 0) {
                                const empty = document.createElement('div');
                                empty.className = 'chat-empty-hint';
                                empty.dataset.emptyHint = postId;
                                empty.innerHTML = '<div class="empty-hint-icon">💬</div><p class="empty-hint-text">Hozircha izohlar yo‘q. Birinchi bo‘lib suhbatni boshlang!</p>';
                                state.stream.appendChild(empty);
                            }
                        }
                    }, 200);
                }

                if (data.comments_count !== undefined && postId) {
                    updatePostCommentsBadge(postId, data.comments_count);
                }
            }
        } catch (err) {
            console.error('Delete comment failed:', err);
            alert('Izohni o‘chirishda xatolik yuz berdi.');
            delBtn.disabled = false;
        }
    });

    // ─── Quick Emoji Chips ──────────────────────────────────────
    document.addEventListener('click', (event) => {
        const emojiBtn = event.target.closest('.quick-emoji-btn');
        if (!emojiBtn) return;
        event.preventDefault();

        const emoji = emojiBtn.dataset.emoji || emojiBtn.textContent.trim().split(' ')[0];
        const chatEl = emojiBtn.closest('.post-comments-chat');
        if (!chatEl) return;

        const input = chatEl.querySelector('.comment-live-input');
        if (input) {
            input.value = (input.value ? input.value + ' ' : '') + emoji + ' ';
            input.focus();
        }
    });

    // ─── Toggle Chat Visibility Button ──────────────────────────
    document.addEventListener('click', (event) => {
        const toggleBtn = event.target.closest('.js-toggle-chat, .toggle-chat-btn');
        if (!toggleBtn) return;
        event.preventDefault();

        const postId = toggleBtn.dataset.toggleChatPost;
        if (!postId) return;

        const chatEl = document.getElementById(`post-chat-section-${postId}`);
        if (!chatEl) return;

        chatEl.classList.toggle('is-hidden');
        if (!chatEl.classList.contains('is-hidden')) {
            const input = chatEl.querySelector('.comment-live-input');
            if (input) input.focus();
            const stream = chatEl.querySelector('[data-comment-stream]');
            if (stream) stream.scrollTop = stream.scrollHeight;
        }
    });

    // ─── Share / Copy Link ────────────────────────────────────
    document.querySelectorAll('[data-copy-link]').forEach(btn => {
        btn.addEventListener('click', async () => {
            const path = btn.getAttribute('data-copy-link');
            const url = window.location.origin + path;
            try {
                await navigator.clipboard.writeText(url);
                const textSpan = btn.querySelector('span');
                const orig = textSpan ? textSpan.textContent : '';
                if (textSpan) textSpan.textContent = 'Nusxalandi! ✓';
                setTimeout(() => {
                    if (textSpan) textSpan.textContent = orig;
                }, 2000);
            } catch (err) {
                console.log('Copy failed', err);
            }
        });
    });
});