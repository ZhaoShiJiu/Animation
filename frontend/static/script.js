document.addEventListener('DOMContentLoaded', () => {
    const config = {
        apiBaseUrl: '', 
        defaultLang: 'zh',
    };

    const translations = {
        heroTitle: { zh: "ZSJ-观想录", en: "ZSJ-Guanxianglu" },
        startCreatingTitle: { zh: "生成", en: "Generate" },
        githubrepo: { zh: "Github 开源仓库", en: "ZSJ Github Repo" },
        officialWebsite: { zh: "ZSJ 开源社区", en: "ZSJ Open Source Community" },
        groupChat: { zh: "联系我们/加入交流群", en: "Contact Us" },
        placeholders: {
            zh: ["输入一个概念", "微积分的几何原理", "黑洞是如何形成的", "冒泡排序","雷达信道"],
            en: ["Enter a concept", "What is Heat Death?", "How are black holes formed?", "What is Bubble Sort?"]
        },
        chatRailEyebrow: { zh: "MODEL OUTPUT", en: "MODEL OUTPUT" },
        chatRailTitle: { zh: "全量流式输出", en: "Full streaming output" },
        chatRailBody: { zh: "每个 token 都会被保留；解析成功后自动渲染动画，解析失败时可一键重新生成。", en: "Every token is preserved. Valid output renders automatically; parse failures can be regenerated in one click." },
        chatHeaderEyebrow: { zh: "LIVE SESSION", en: "LIVE SESSION" },
        chatHeaderTitle: { zh: "ZSJ-观想录生成台", en: "ZSJ-Guanxianglu Studio" },
        chatLivePill: { zh: "SSE 流式连接", en: "SSE stream" },
        rawOutputEyebrow: { zh: "RAW RESPONSE", en: "RAW RESPONSE" },
        rawOutputTitle: { zh: "知识 -> 视频", en: "Complete model output" },
        parseRetryEyebrow: { zh: "PARSE FAILED", en: "PARSE FAILED" },
        parseRetryTitle: { zh: "输出已完整保留，但暂时无法渲染动画", en: "The output is preserved, but it cannot be rendered yet" },
        parseRetryBody: { zh: "是否使用同一提示词重新生成一次？", en: "Regenerate with the same prompt?" },
        parseRetryButton: { zh: "重新生成", en: "Regenerate" },
        settings: { zh: "", en: "" },
        settingsTitle: { zh: "专业配置", en: "Professional settings" },
        settingsEyebrow: { zh: "CONFIGURATION", en: "CONFIGURATION" },
        settingsPanelTitle: { zh: "生成前配置", en: "Configure before generation" },
        settingsConfirm: { zh: "确认生成", en: "Confirm generation" },
        closeTitle: { zh: "关闭", en: "Close" },
        styleLabel: { zh: "视觉风格", en: "Visual style" },
        styleCinematic: { zh: "电影叙事", en: "Cinematic" },
        styleMinimal: { zh: "极简专业", en: "Minimal" },
        styleAcademic: { zh: "教学讲解", en: "Academic" },
        styleFuturistic: { zh: "未来科技", en: "Futuristic" },
        durationLabel: { zh: "视频节奏", en: "Pacing" },
        durationPreview: { zh: "快速预览", en: "Quick preview" },
        previewConfirmTitle: { zh: "当前为快速预览模式，如需全量生成请选择其他 视频节奏 ，是否继续？", en: "Quick preview mode is selected. Choose another video pacing option for full generation. Continue?" },
        previewConfirmCancel: { zh: "返回修改", en: "Go back" },
        previewConfirmContinue: { zh: "继续生成", en: "Continue" },
        durationShort: { zh: "短：30 秒", en: "Short: 30s" },
        durationMedium: { zh: "标准：60 秒", en: "Standard: 60s" },
        durationLong: { zh: "长：90 秒", en: "Long: 90s" },
        ratioLabel: { zh: "画幅比例", en: "Aspect ratio" },
        resolutionLabel: { zh: "容器尺寸", en: "Container size" },
        depthLabel: { zh: "讲解深度", en: "Depth" },
        depthStarter: { zh: "入门", en: "Starter" },
        depthStandard: { zh: "标准", en: "Standard" },
        depthExpert: { zh: "专业", en: "Expert" },
        narrationLabel: { zh: "强化文案", en: "Enhanced copy" },
        bilingualLabel: { zh: "双语字幕", en: "Bilingual subtitles" },
        mathjaxLabel: { zh: "使用 MathJax", en: "Use MathJax" },
        newChat: { zh: "新对话", en: "New Chat" },
        newChatTitle: { zh: "新对话", en: "New Chat" },
        generationConfig: { zh: "生成配置", en: "Generation settings" },
        stopGeneration: { zh: "停止", en: "Stop" },
        cancelQueuedTask: { zh: "取消任务", en: "Cancel task" },
        generationStopped: { zh: "用户主动停止任务", en: "Task stopped by user" },
        generationQueued: { zh: "任务正在排队，请稍候...", en: "Your generation task is queued. Please wait..." },
        generationStarted: { zh: "任务已开始执行", en: "Generation has started" },
        openWindowTip: { zh: "新窗口中打开效果更好", en: "It looks better in a new window" },
        openWindowTipBody: { zh: "局限于浏览器容器排布，原视频容器尺寸不能完美契合", en: "Due to browser container layout limits, the original video container size may not fit perfectly." },
        chatPlaceholder: {
            zh: "AI 生成结果具有随机性，您可在此输入修改意见",
            en: "Results are random. Enter your modifications here for adjustments."
        },
        sendTitle: { zh: "发送", en: "Send" },
        agentThinking: { zh: "ZSJ Agent 正在进行思考与规划，请稍后。这可能需要数十秒至数分钟...", en: "ZSJ Agent is thinking and planning, please wait..." },
        generatingCode: { zh: "生成代码中...", en: "Generating code..." },
        codeComplete: { zh: "代码已完成", en: "Code generated" },
        openInNewWindow: { zh: "在新窗口中打开", en: "Open in new window" },
        saveAsHTML: { zh: "保存为 HTML", en: "Save as HTML" },
        shareHTMLLink: { zh: "分享 HTML 链接", en: "Share HTML link" },
        shareExpirationLabel: { zh: "链接有效期", en: "Link expiration" },
        shareExpire1h: { zh: "1 小时", en: "1 hour" },
        shareExpire3h: { zh: "3 小时", en: "3 hours" },
        shareExpire6h: { zh: "6 小时", en: "6 hours" },
        shareExpire8h: { zh: "8 小时", en: "8 hours" },
        shareExpire1d: { zh: "1 天", en: "1 day" },
        shareExpire3d: { zh: "3 天", en: "3 days" },
        shareExpire7d: { zh: "7 天", en: "7 days" },
        shareExpireForever: { zh: "永久", en: "Forever" },
        sharePasswordLabel: { zh: "访问密码", en: "Access password" },
        sharePasswordPlaceholder: { zh: "请输入 4-20 位数字密码", en: "Enter a 4-20 digit password" },
        shareCreateLink: { zh: "创建并复制链接", en: "Create and copy link" },
        shareCopyDetails: { zh: "复制详细信息", en: "Copy details" },
        shareDetailsCopied: { zh: "分享详细信息已复制", en: "Share details copied" },
        sharePasswordRequired: { zh: "请输入 4-20 位数字密码", en: "Enter a 4-20 digit password" },
        shareResultUrl: { zh: "链接", en: "Link" },
        shareResultStart: { zh: "生效时间", en: "Starts at" },
        shareResultEnd: { zh: "失效时间", en: "Expires at" },
        shareNeverExpires: { zh: "永久有效", en: "Never expires" },
        shareResultPassword: { zh: "访问密码", en: "Access password" },
        htmlLinkCopied: { zh: "HTML 链接已复制，详细信息如下", en: "HTML link copied. Details are shown below." },
        shareFailed: { zh: "分享链接创建失败", en: "Failed to create share link" },
        exportAsVideo: { zh: "导出为视频", en: "Export as Video" },
        featureComingSoon: { zh: "该功能正在开发中，将在不久的将来推出。\n 请关注我的官方 GitHub 仓库以获取最新动态！", en: "This feature is under development and will be available soon.\n Follow our official GitHub repository for the latest updates!" },
        visitGitHub: { zh: "访问 GitHub", en: "Visit GitHub" },
        exportResolutionLabel: { zh: "输出分辨率", en: "Output resolution" },
        exportFpsLabel: { zh: "帧率", en: "Frame rate" },
        exportExpirationLabel: { zh: "文件保留时间", en: "File retention" },
        exportStartRender: { zh: "开始渲染", en: "Start rendering" },
        exportInitializing: { zh: "初始化中...", en: "Initializing..." },
        exportDownloadVideo: { zh: "下载 MP4", en: "Download MP4" },
        exportRendering: { zh: "渲染中...", en: "Rendering..." },
        exportRetention10m: { zh: "10 分钟", en: "10 minutes" },
        exportRetention1h: { zh: "1 小时", en: "1 hour" },
        exportRetention6h: { zh: "6 小时", en: "6 hours" },
        exportRetention1d: { zh: "1 天", en: "1 day" },
        exportRetention7d: { zh: "7 天", en: "7 days" },
        errorMessage: { zh: "抱歉，服务出现了一点问题。请稍后重试。", en: "Sorry, something went wrong. Please try again later." },
        errorFetchFailed: {zh: "LLM服务不可用，请稍后再试", en: "LLM service is unavailable. Please try again later."},
        errorTooManyRequests: {zh: "今天已经使用太多，请明天再试", en: "Too many requests today. Please try again tomorrow."},
        errorLLMParseError: {zh: "返回的动画代码解析失败，请调整提示词重新生成。", en: "Failed to parse the returned animation code. Please adjust your prompt and try again."},
        errorDetailsLabel: { zh: "错误详情", en: "Error details" },
        passphraseEyebrow: { zh: "ACCESS", en: "ACCESS" },
        passphraseTitle: { zh: "请输入暗号", en: "Enter passphrase" },
        passphrasePlaceholder: { zh: "暗号", en: "Passphrase" },
        passphraseSubmit: { zh: "进入", en: "Enter" },
        passphraseError: { zh: "暗号错误", en: "Invalid passphrase" },
        paperExplain: { zh: "论文解释", en: "Explain paper" },
        paperUploadTitle: { zh: "上传 PDF 论文", en: "Upload PDF paper" },
        paperFileLabel: { zh: "论文 PDF", en: "Paper PDF" },
        paperFocusLabel: { zh: "指定章节或概念（可选）", en: "Section or concept to explain (optional)" },
        paperFocusPlaceholder: { zh: "例如：第三章方法、Transformer 注意力机制、实验结果", en: "E.g. Method section, Transformer attention, experiment results" },
        paperContinueConfig: { zh: "继续配置", en: "Continue to settings" },
        paperFileRequired: { zh: "请先上传 PDF 论文", en: "Please upload a PDF paper first" },
        paperOnlyPdf: { zh: "仅支持 PDF 文件", en: "Only PDF files are supported" },
        paperThinking: { zh: "ZSJ Agent 正在阅读论文并规划动画讲解，请稍后。这可能需要数十秒至数分钟...", en: "ZSJ Agent is reading the paper and planning the animation. This may take tens of seconds to minutes..." },
        paperUserMessage: { zh: "论文解释", en: "Paper explanation" },
        paperFocusPrefix: { zh: "指定内容", en: "Focus" },
        mobileUnsupported: { zh: "请在PC端访问，移动端暂不支持", en: "Please visit on a PC. Mobile is not supported yet." },
    };

    let currentLang = config.defaultLang;
    const body = document.body;
    const passphraseGate = document.getElementById('passphrase-gate');
    const passphraseForm = document.getElementById('passphrase-form');
    const passphraseInput = document.getElementById('passphrase-input');
    const passphraseError = document.getElementById('passphrase-error');
    const initialForm = document.getElementById('initial-form');
    const initialInput = document.getElementById('initial-input');
    const paperExplainButton = document.getElementById('paper-explain-button');
    const paperUploadModal = document.getElementById('paper-upload-modal');
    const paperUploadForm = document.getElementById('paper-upload-form');
    const paperFileInput = document.getElementById('paper-file-input');
    const paperFileName = document.getElementById('paper-file-name');
    const paperFocusInput = document.getElementById('paper-focus-input');
    const paperUploadClose = document.getElementById('paper-upload-close');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatLog = document.getElementById('chat-log');
    const chatRailTitle = document.querySelector('[data-translate-key="chatRailTitle"]');
    const chatRailBody = document.querySelector('[data-translate-key="chatRailBody"]');
    const stopGenerationButton = document.getElementById('stop-generation-button');
    const queueCancelButton = document.getElementById('queue-cancel-button');
    const newChatButton = document.getElementById('new-chat-button');
    const languageSwitcher = document.getElementById('language-switcher');
    const placeholderContainer = document.getElementById('animated-placeholder');
    const featureModal = document.getElementById('feature-modal');
    const exportModal = document.getElementById('export-modal');
    const exportForm = document.getElementById('export-form');
    const exportResolution = document.getElementById('export-resolution');
    const exportFps = document.getElementById('export-fps');
    const exportExpiration = document.getElementById('export-expiration');
    const exportStartButton = document.getElementById('export-start-button');
    const exportModalClose = document.getElementById('export-modal-close');
    const exportProgress = document.getElementById('export-progress');
    const exportProgressBar = document.getElementById('export-progress-bar');
    const exportProgressText = document.getElementById('export-progress-text');
    const exportProgressPercent = document.getElementById('export-progress-percent');
    const exportResult = document.getElementById('export-result');
    const exportDownloadButton = document.getElementById('export-download-button');
    const previewConfirmModal = document.getElementById('preview-confirm-modal');
    const previewConfirmClose = document.getElementById('preview-confirm-close');
    const previewConfirmCancel = document.getElementById('preview-confirm-cancel');
    const previewConfirmContinue = document.getElementById('preview-confirm-continue');
    const shareModal = document.getElementById('share-modal');
    const shareForm = document.getElementById('share-form');
    const shareExpiration = document.getElementById('share-expiration');
    const sharePassword = document.getElementById('share-password');
    const shareSubmitButton = document.getElementById('share-submit-button');
    const shareResult = document.getElementById('share-result');
    const shareResultUrl = document.getElementById('share-result-url');
    const shareResultStart = document.getElementById('share-result-start');
    const shareResultEnd = document.getElementById('share-result-end');
    const shareResultPassword = document.getElementById('share-result-password');
    const shareQr = document.getElementById('share-qr');
    const shareModalCloseButton = document.getElementById('share-modal-close-button');
    const modalGitHubButton = document.getElementById('modal-github-button');
    const modalCloseButton = document.getElementById('modal-close-button');
    const settingsPanel = document.getElementById('settings-panel');
    const settingsToggles = document.querySelectorAll('[data-settings-toggle]');
    const settingsClose = document.getElementById('settings-close');
    const settingsConfirm = document.getElementById('settings-confirm');
    const settingStyle = document.getElementById('setting-style');
    const settingDuration = document.getElementById('setting-duration');
    const settingRatio = document.getElementById('setting-ratio');
    const settingResolution = document.getElementById('setting-resolution');
    const settingDepth = document.getElementById('setting-depth');
    const settingNarration = document.getElementById('setting-narration');
    const settingBilingual = document.getElementById('setting-bilingual');
    const settingMathjax = document.getElementById('setting-mathjax');

    const templates = {
        user: document.getElementById('user-message-template'),
        status: document.getElementById('agent-status-template'),
        output: document.getElementById('agent-output-template'),
        retry: document.getElementById('parse-retry-template'),
        player: document.getElementById('animation-player-template'),
        'copy-review': document.getElementById('copy-review-template'),
        error: document.getElementById('agent-error-template'),
    };

    class LLMParseError extends Error {
        constructor(message, code = 'LLM_UNKNOWN_ERROR') {
            super(message);
            this.name = 'LLMParseError';
            this.code = code;
        }
    }

    let conversationHistory = [];
    let accumulatedCode = '';
    let placeholderInterval;
    let oneQuoteInterval;
    let activeGenerationController = null;
    let pendingGenerationTopic = '';
    let pendingGenerationIsInitial = false;
    let pendingGenerationMode = 'concept';
    let pendingPaperFile = null;
    let pendingPaperFocus = '';
    let pendingShareHtml = '';
    let pendingExportHtml = '';
    let latestShareDetails = null;
    let previewConfirmResolver = null;
    let currentCopyJson = null;
    let copyReviewElement = null;
    let isCopyEditing = false;

    function unlockPassphraseGate() {
        passphraseGate?.classList.add('hidden');
        sessionStorage.setItem('passphraseVerified', '1');
        initialInput?.focus();
    }

    async function initPassphraseGate() {
        try {
            const response = await fetch(`${config.apiBaseUrl}/config`);
            if (!response.ok) throw new Error('Failed to load config');
            const publicConfig = await response.json();
            if (!publicConfig.requiresPassphrase || sessionStorage.getItem('passphraseVerified') === '1') {
                unlockPassphraseGate();
            }
        } catch (error) {
            Logger.warn('Failed to initialize passphrase gate:', error);
        }
    }

    async function handlePassphraseSubmit(e) {
        e.preventDefault();
        const passphrase = passphraseInput.value.trim();
        if (!passphrase) return;

        try {
            const response = await fetch(`${config.apiBaseUrl}/verify-passphrase`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ passphrase }),
            });
            if (!response.ok) throw new Error('Invalid passphrase');
            unlockPassphraseGate();
        } catch (error) {
            passphraseError.hidden = false;
            passphraseInput.select();
        }
    }

    function getGenerationSettings() {
        return {
            style: settingStyle?.value || 'minimal',
            duration: settingDuration?.value || 'medium',
            ratio: settingRatio?.value || '16:9',
            resolution: settingResolution?.value || '1080p',
            depth: settingDepth?.value || 'standard',
            narration: Boolean(settingNarration?.checked),
            bilingual: Boolean(settingBilingual?.checked),
            mathjax: Boolean(settingMathjax?.checked),
        };
    }

    function isMobileDevice() {
        const hasCoarsePointer = window.matchMedia?.('(pointer: coarse)').matches;
        const narrowViewport = Math.min(window.innerWidth, window.innerHeight) < 768;
        const mobileAgent = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
        return mobileAgent || (hasCoarsePointer && narrowViewport);
    }

    function showMobileUnsupportedWarning() {
        if (!isMobileDevice()) return;
        showWarning(translations.mobileUnsupported[currentLang], { persistent: true, blocking: true });
    }

    async function loadOneQuotes() {
        try {
            const response = await fetch('/static/one-quotes.json');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const quotes = await response.json();
            if (!Array.isArray(quotes) || quotes.length === 0) return;

            let index = Math.floor(Math.random() * quotes.length);
            const showQuote = () => {
                const quote = quotes[index % quotes.length];
                [chatRailTitle, chatRailBody].forEach(element => element?.classList.add('is-changing'));
                window.setTimeout(() => {
                    if (chatRailTitle) chatRailTitle.textContent = quote.text;
                    if (chatRailBody) chatRailBody.textContent = quote.source;
                    [chatRailTitle, chatRailBody].forEach(element => element?.classList.remove('is-changing'));
                }, 260);
                index += 1;
            };

            const scheduleNextQuote = () => {
                const delay = 8000 + Math.random() * 4000;
                oneQuoteInterval = window.setTimeout(() => {
                    showQuote();
                    scheduleNextQuote();
                }, delay);
            };

            showQuote();
            if (oneQuoteInterval) clearTimeout(oneQuoteInterval);
            scheduleNextQuote();
        } catch (error) {
            Logger.warn('Failed to load ONE quotes:', error);
        }
    }

    function handleFormSubmit(e) {
        e.preventDefault();
        const isInitial = e.currentTarget.id === 'initial-form';
        const input = isInitial ? initialInput : chatInput;
        const topic = input.value.trim();
        if (!topic) return;

        if (!isInitial) {
            conversationHistory.push({ role: 'user', content: topic });
            startGeneration(topic);
            chatInput.value = '';
            return;
        }

        pendingGenerationMode = 'concept';
        pendingGenerationTopic = topic;
        pendingGenerationIsInitial = true;
        openSettingsPanel(true);
    }

    function updatePaperFileName() {
        if (!paperFileName) return;
        paperFileName.textContent = paperFileInput?.files?.[0]?.name || '';
    }

    function openPaperUploadModal() {
        paperUploadModal?.classList.add('visible');
        paperFileInput && (paperFileInput.value = '');
        paperFocusInput && (paperFocusInput.value = '');
        updatePaperFileName();
        paperFileInput?.focus();
    }

    function closePaperUploadModal() {
        paperUploadModal?.classList.remove('visible');
    }

    function isPdfFile(file) {
        return Boolean(file && (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')));
    }

    function handlePaperUploadSubmit(e) {
        e.preventDefault();
        const file = paperFileInput?.files?.[0];
        if (!file) {
            showWarning(translations.paperFileRequired[currentLang]);
            return;
        }
        if (!isPdfFile(file)) {
            showWarning(translations.paperOnlyPdf[currentLang]);
            return;
        }

        pendingGenerationMode = 'paper';
        pendingPaperFile = file;
        pendingPaperFocus = paperFocusInput?.value.trim() || '';
        closePaperUploadModal();
        openSettingsPanel(true);
    }

    async function consumeGenerationResponse(response, displayTopic, agentThinkingMessage, outputElement, options = {}) {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullResponse = '';
        let queueWarningVisible = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;

                const jsonStr = line.substring(6);
                if (jsonStr.includes('[DONE]')) {
                    accumulatedCode = extractHtmlFromResponse(fullResponse);
                    if (options.saveAssistantHistory !== false) {
                        conversationHistory.push({ role: 'assistant', content: fullResponse });
                    }
                    markOutputAsComplete(outputElement);

                    if (!accumulatedCode || !isHtmlContentValid(accumulatedCode)) {
                        Logger.warn('Unable to parse renderable HTML from full response:', fullResponse.substring(0, 200));
                        appendRetryPrompt(displayTopic);
                        scrollToBottom();
                        return;
                    }

                    try {
                        appendAnimationPlayer(accumulatedCode, displayTopic);
                    } catch (err) {
                        Logger.error('appendAnimationPlayer failed:', err);
                        appendRetryPrompt(displayTopic);
                        scrollToBottom();
                        return;
                    }

                    scrollToBottom();
                    return;
                }

                let data;
                try {
                    data = JSON.parse(jsonStr);
                } catch (err) {
                    Logger.error('Failed to parse JSON:', jsonStr.substring(0, 200));
                    throw new LLMParseError('Invalid response format from server.');
                }

                if (data.event === 'queued') {
                    queueWarningVisible = true;
                    showWarning(translations.generationQueued[currentLang], {
                        persistent: true,
                        blocking: true,
                        loading: true,
                        cancelable: true,
                        cancelText: translations.cancelQueuedTask[currentLang],
                    });
                    continue;
                }

                if (data.event === 'started') {
                    if (queueWarningVisible) {
                        forceHideWarning();
                        showWarning(translations.generationStarted[currentLang]);
                        queueWarningVisible = false;
                    }
                    continue;
                }

                if (data.event === 'reset') {
                    fullResponse = '';
                    if (outputElement) {
                        const codeEl = outputElement.querySelector('code');
                        if (codeEl) codeEl.innerHTML = '';
                    }
                    continue;
                }

                if (data.error) throw new LLMParseError(data.error);

                const token = data.token || '';
                if (agentThinkingMessage) agentThinkingMessage.remove();
                fullResponse += token;
                updateOutputBlock(outputElement, token);
            }
        }
    }

    async function startGeneration(topic, options = {}) {
        Logger.info('Getting generation from backend.');
        if (!options.reuseUserMessage) appendUserMessage(topic);
        const agentThinkingMessage = appendAgentStatus(translations.agentThinking[currentLang]);
        const submitButton = document.querySelector('.submit-button');
        activeGenerationController = new AbortController();
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.classList.add('disabled');
        }
        if (stopGenerationButton) stopGenerationButton.hidden = false;
        accumulatedCode = '';
        const outputElement = appendOutputBlock();

        try {
            const response = await fetch(`${config.apiBaseUrl}/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic: topic, history: conversationHistory, settings: getGenerationSettings() }),
                signal: activeGenerationController.signal
            });
            await consumeGenerationResponse(response, topic, agentThinkingMessage, outputElement);
        } catch (error) {
            Logger.error("Streaming failed:", error);
            if (agentThinkingMessage) agentThinkingMessage.remove();

            let displayMessage = translations.errorFetchFailed[currentLang];
            if (error.name === 'AbortError') {
                displayMessage = translations.generationStopped[currentLang];
            } else if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
                displayMessage = translations.errorFetchFailed[currentLang];
            } else if (error.message.includes('status: 429')) {
                displayMessage = translations.errorTooManyRequests[currentLang];
            } else if (error instanceof LLMParseError) {
                displayMessage = translations.errorLLMParseError[currentLang];
            }

            showWarning(displayMessage);
            appendErrorMessage(translations.errorMessage[currentLang], error);
            if (outputElement) markOutputAsComplete(outputElement);
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.classList.remove('disabled');
            }
            if (stopGenerationButton) stopGenerationButton.hidden = true;
            activeGenerationController = null;
        }
    }

    async function startPaperGeneration(file, focus, displayTopic) {
        if (!file) return;
        if (!displayTopic) displayTopic = `${translations.paperUserMessage[currentLang]}：${file.name}`;
        appendUserMessage(displayTopic);
        const agentThinkingMessage = appendAgentStatus(translations.paperThinking[currentLang]);
        const submitButton = document.querySelector('.submit-button');
        activeGenerationController = new AbortController();
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.classList.add('disabled');
        }
        if (stopGenerationButton) stopGenerationButton.hidden = false;
        accumulatedCode = '';
        const outputElement = appendOutputBlock();
        const formData = new FormData();
        formData.append('pdf', file);
        formData.append('focus', focus || '');
        formData.append('settings', JSON.stringify(getGenerationSettings()));

        try {
            const response = await fetch(`${config.apiBaseUrl}/paper/generate`, {
                method: 'POST',
                body: formData,
                signal: activeGenerationController.signal
            });
            await consumeGenerationResponse(response, displayTopic, agentThinkingMessage, outputElement, { saveAssistantHistory: false });
        } catch (error) {
            Logger.error("Paper streaming failed:", error);
            if (agentThinkingMessage) agentThinkingMessage.remove();

            let displayMessage = translations.errorFetchFailed[currentLang];
            if (error.name === 'AbortError') {
                displayMessage = translations.generationStopped[currentLang];
            } else if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
                displayMessage = translations.errorFetchFailed[currentLang];
            } else if (error.message.includes('status: 429')) {
                displayMessage = translations.errorTooManyRequests[currentLang];
            } else if (error instanceof LLMParseError) {
                displayMessage = translations.errorLLMParseError[currentLang];
            }

            showWarning(displayMessage);
            appendErrorMessage(translations.errorMessage[currentLang], error);
            if (outputElement) markOutputAsComplete(outputElement);
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.classList.remove('disabled');
            }
            if (stopGenerationButton) stopGenerationButton.hidden = true;
            activeGenerationController = null;
        }
    }

    function switchToChatView() {
        body.classList.remove('show-initial-view');
        body.classList.add('show-chat-view');
        languageSwitcher?.style && (languageSwitcher.style.display = 'none');
    }

    function openSettingsPanel(isBeforeGeneration = false) {
        settingsPanel.classList.add('visible');
        settingsPanel.setAttribute('aria-hidden', 'false');
        settingsToggles.forEach(button => button.classList.toggle('is-attention', isBeforeGeneration));
    }

    function closeSettingsPanel() {
        settingsPanel.classList.remove('visible');
        settingsPanel.setAttribute('aria-hidden', 'true');
        settingsToggles.forEach(button => button.classList.remove('is-attention'));
    }

    function showPreviewConfirm() {
        previewConfirmModal.classList.add('visible');
        return new Promise(resolve => {
            previewConfirmResolver = resolve;
        });
    }

    function resolvePreviewConfirm(confirmed) {
        previewConfirmModal.classList.remove('visible');
        if (!previewConfirmResolver) return;
        previewConfirmResolver(confirmed);
        previewConfirmResolver = null;
    }

    async function confirmGenerationFromSettings() {
        if (pendingGenerationMode === 'paper') {
            if (!pendingPaperFile) {
                closeSettingsPanel();
                return;
            }

            if (settingDuration?.value === 'preview' && !await showPreviewConfirm()) {
                return;
            }

            switchToChatView();
            const displayTopic = `${translations.paperUserMessage[currentLang]}：${pendingPaperFile.name}${pendingPaperFocus ? `\n${translations.paperFocusPrefix[currentLang]}：${pendingPaperFocus}` : ''}`;
            startPaperGeneration(pendingPaperFile, pendingPaperFocus, displayTopic);
            pendingPaperFile = null;
            pendingPaperFocus = '';
            pendingGenerationMode = 'concept';
            closeSettingsPanel();
            return;
        }

        const topic = pendingGenerationTopic;
        if (!topic) {
            closeSettingsPanel();
            return;
        }

        if (settingDuration?.value === 'preview' && !await showPreviewConfirm()) {
            return;
        }

        if (pendingGenerationIsInitial) switchToChatView();

        conversationHistory.push({ role: 'user', content: topic });
        // Use the new two-stage flow: generate copy first, then animation
        generateCopy(topic);
        if (pendingGenerationIsInitial) {
            initialInput.value = '';
            placeholderContainer?.classList?.remove('hidden');
        } else {
            chatInput.value = '';
        }
        pendingGenerationTopic = '';
        pendingGenerationIsInitial = false;
        pendingGenerationMode = 'concept';
        closeSettingsPanel();
    }

    // ── 复制按钮 ──
    var COPY_ICON_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';
    var CHECK_ICON_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';

    function createCopyButton(messageElement) {
        if (!messageElement) return null;
        // 跳过思考和重试消息
        if (messageElement.querySelector('.status-bubble')) return null;
        if (messageElement.classList.contains('has-retry')) return null;

        var btn = document.createElement('button');
        btn.className = 'message-copy-btn';
        btn.type = 'button';
        btn.title = '复制';
        btn.innerHTML = COPY_ICON_SVG + ' <span class="copy-label">复制</span>';

        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();

            // 即时视觉反馈
            btn.style.transform = 'scale(0.9)';
            setTimeout(function () { btn.style.transform = ''; }, 120);

            var text = getMessageText(messageElement);
            if (!text) {
                btn.style.outline = '2px solid #f59e0b';
                btn.style.outlineOffset = '1px';
                setTimeout(function () { btn.style.outline = ''; btn.style.outlineOffset = ''; }, 600);
                return;
            }

            tryCopy(text, btn);
        });

        return btn;
    }

    function getMessageText(el) {
        // 1. 大模型输出代码
        var code = el.querySelector('.raw-output code');
        if (code) {
            var t = code.textContent || '';
            if (t.trim()) return t.trim();
        }

        // 2. 错误详情
        var err = el.querySelector('.error-detail-text');
        if (err) {
            var t = err.textContent || '';
            if (t.trim()) return t.trim();
        }

        // 3. 用户消息
        var bubble = el.querySelector('.message-bubble');
        if (bubble) {
            var t = bubble.textContent || '';
            if (t.trim()) return t.trim();
        }

        // 4. 文案评审
        var review = el.querySelector('.copy-review-card');
        if (review) {
            var parts = [];
            var title = review.querySelector('.copy-title');
            if (title && title.textContent) parts.push(title.textContent.trim());
            review.querySelectorAll('.act-card').forEach(function (act) {
                act.querySelectorAll('.act-field').forEach(function (f) {
                    var lb = f.querySelector('label');
                    var vl = f.querySelector('span, input, textarea');
                    if (lb && vl) {
                        var v = vl.value !== undefined ? vl.value : vl.textContent;
                        if (v && v.trim()) parts.push(lb.textContent.trim() + ': ' + v.trim());
                    }
                });
            });
            if (parts.length) return parts.join('\n\n');
        }

        // 5. 兜底
        return (el.textContent || '').trim();
    }

    function tryCopy(text, btn) {
        // 方法1: execCommand
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0;pointer-events:none;';
        ta.readOnly = true;
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        try { ta.setSelectionRange(0, 999999); } catch (e) {}

        var ok = false;
        try { ok = document.execCommand('copy'); } catch (e) {}

        document.body.removeChild(ta);

        if (ok) {
            onCopyDone(btn, true);
            return;
        }

        // 方法2: Clipboard API
        if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
            navigator.clipboard.writeText(text).then(
                function () { onCopyDone(btn, true); },
                function () { onCopyDone(btn, false); }
            );
        } else {
            onCopyDone(btn, false);
        }
    }

    function onCopyDone(btn, success) {
        if (success) {
            btn.classList.add('copied');
            btn.innerHTML = CHECK_ICON_SVG + ' <span class="copy-label">已复制</span>';
            btn.title = '已复制 ✓';
        } else {
            btn.classList.add('copy-failed');
            btn.title = '复制失败，请手动选择';
        }
        clearTimeout(window._copyTimer);
        window._copyTimer = setTimeout(function () {
            btn.classList.remove('copied', 'copy-failed');
            btn.innerHTML = COPY_ICON_SVG + ' <span class="copy-label">复制</span>';
            btn.title = '复制';
        }, success ? 1500 : 2500);
    }

    function attachCopyButton(element) {
        var btn = createCopyButton(element);
        if (btn) element.appendChild(btn);
    }

    function appendFromTemplate(template, text) {
        const node = template.content.cloneNode(true);
        const element = node.firstElementChild;
        if (text) element.innerHTML = element.innerHTML.replace('${text}', text);
        element.querySelectorAll('[data-translate-key]').forEach(el => {
            const key = el.dataset.translateKey;
            const translation = translations[key]?.[currentLang];
            if (translation) el.textContent = translation;
        });
        chatLog.appendChild(element);
        attachCopyButton(element);
        scrollToBottom();
        return element;
    }

    const appendUserMessage = (text) => appendFromTemplate(templates.user, text);
    const appendAgentStatus = (text) => appendFromTemplate(templates.status, text);
    function appendErrorMessage(text, error) {
        const element = appendFromTemplate(templates.error, text);
        const detailText = element.querySelector('.error-detail-text');
        if (detailText) {
            const message = error?.stack || error?.message || String(error || 'Unknown error');
            detailText.textContent = `${translations.errorDetailsLabel[currentLang]}\n${message}`;
        }
        return element;
    }
    const appendOutputBlock = () => appendFromTemplate(templates.output);

    function updateOutputBlock(outputElement, text) {
        const codeElement = outputElement.querySelector('code');
        if (!text || !codeElement) return;
        const span = document.createElement('span');
        span.textContent = text;
        codeElement.appendChild(span);

        const rawOutput = outputElement.querySelector('.raw-output');
        if (rawOutput) {
            requestAnimationFrame(() => {
                rawOutput.scrollTop = rawOutput.scrollHeight;
            });
        }
    }

    function markOutputAsComplete(outputElement) {
        outputElement?.querySelector('.output-card')?.classList.remove('is-streaming');
        const status = outputElement?.querySelector('.output-status');
        if (status) status.textContent = translations.codeComplete[currentLang];
    }

    function extractHtmlFromResponse(responseText) {
        if (!responseText) return '';

        // Step 1: Strip leading/trailing markdown code fences
        let text = responseText.trim();
        // Remove leading ```html or ``` (with optional language)
        text = text.replace(/^```(?:html|HTML)?\s*\n?/, '');
        // Remove trailing ```
        text = text.replace(/\n?```\s*$/, '');

        // Step 2: If the text contains fenced code blocks, extract the HTML one
        var fencePattern = /```(?:html|HTML)?\s*\n([\s\S]*?)\n```/g;
        var fenceMatch;
        var htmlBlocks = [];
        while ((fenceMatch = fencePattern.exec(text)) !== null) {
            var block = fenceMatch[1].trim();
            if (/<html|<body|<div/i.test(block)) {
                htmlBlocks.push(block);
            }
        }
        if (htmlBlocks.length > 0) {
            // Use the longest HTML-looking block
            text = htmlBlocks.reduce(function(a, b) { return a.length >= b.length ? a : b; });
        }

        // Step 3: Find the HTML document boundaries
        var htmlStart = text.search(/<html[^>]*>/i);
        var htmlEnd = text.search(/<\/html>/i);
        if (htmlStart !== -1 && htmlEnd !== -1 && htmlEnd > htmlStart) {
            return text.substring(htmlStart, htmlEnd + 7).trim();
        }

        // Step 4: Fallback — find doctype + content
        var doctypeMatch = text.match(/<!doctype\s+html[^>]*>/i);
        if (doctypeMatch) {
            var fromDoctype = text.substring(doctypeMatch.index);
            // Try to find </html> end
            var endIdx = fromDoctype.search(/<\/html>/i);
            if (endIdx !== -1) {
                return fromDoctype.substring(0, endIdx + 7).trim();
            }
            return fromDoctype.trim();
        }

        // Step 5: Last resort — if text looks like HTML, return as-is
        if (/<body|<div|<style|<script/i.test(text)) {
            return text;
        }

        return '';
    }

    function appendRetryPrompt(topic) {
        const element = appendFromTemplate(templates.retry);
        const button = element.querySelector('.retry-generation');
        button?.addEventListener('click', () => {
            element.remove();
            startGeneration(topic, { reuseUserMessage: true });
        });
        return element;
    }

    function getPreviewSize(settings = getGenerationSettings()) {
        const ratioMap = {
            '16:9': [16, 9],
            '9:16': [9, 16],
            '1:1': [1, 1],
        };
        const heightMap = {
            '720p': 720,
            '1080p': 1080,
            '2k': 1152,
        };
        const [ratioWidth, ratioHeight] = ratioMap[settings.ratio] || ratioMap['16:9'];
        const sourceHeight = heightMap[settings.resolution] || heightMap['1080p'];
        const sourceWidth = Math.round(sourceHeight * ratioWidth / ratioHeight);
        const availableWidth = Math.max((chatLog?.clientWidth || sourceWidth) - 72, 320);
        const availableHeight = Math.max(window.innerHeight * 0.72, 320);
        const scale = Math.min(availableWidth / sourceWidth, availableHeight / sourceHeight, 1);
        return {
            width: Math.round(sourceWidth * scale),
            height: Math.round(sourceHeight * scale),
            sourceWidth,
            sourceHeight,
            scale,
        };
    }

    function createHtmlBlobUrl(htmlContent) {
        const blob = new Blob([htmlContent], { type: 'text/html' });
        return URL.createObjectURL(blob);
    }

    function openShareModal(htmlContent) {
        pendingShareHtml = htmlContent;
        sharePassword.value = '';
        shareExpiration.value = '1h';
        shareResult.hidden = true;
        latestShareDetails = null;
        shareSubmitButton.textContent = translations.shareCreateLink[currentLang];
        shareModal.classList.add('visible');
        sharePassword.focus();
    }

    function closeShareModal() {
        shareModal.classList.remove('visible');
        pendingShareHtml = '';
    }

    function formatShareTime(value) {
        return new Date(value).toLocaleString(currentLang === 'zh' ? 'zh-CN' : 'en-US');
    }

    function getShareDetailsText(data = latestShareDetails) {
        if (!data) return '';
        const expiresAt = data.expiresAt ? formatShareTime(data.expiresAt) : translations.shareNeverExpires[currentLang];
        return [
            `${translations.shareResultUrl[currentLang]}：${data.url}`,
            `${translations.shareResultStart[currentLang]}：${formatShareTime(data.createdAt)}`,
            `${translations.shareResultEnd[currentLang]}：${expiresAt}`,
            `${translations.shareResultPassword[currentLang]}：${data.password}`,
        ].join('\n');
    }

    async function copyShareDetails() {
        await navigator.clipboard.writeText(getShareDetailsText());
        showWarning(translations.shareDetailsCopied[currentLang]);
    }

    function renderShareResult(data) {
        latestShareDetails = data;
        shareResultUrl.value = data.url;
        shareResultStart.textContent = formatShareTime(data.createdAt);
        shareResultEnd.textContent = data.expiresAt ? formatShareTime(data.expiresAt) : translations.shareNeverExpires[currentLang];
        shareResultPassword.textContent = data.password;
        shareResult.hidden = false;
        shareSubmitButton.textContent = translations.shareCopyDetails[currentLang];
        shareQr.src = data.qrCode;
    }

    async function shareHtmlLink(htmlContent, expiresIn, password, previewSize) {
        const response = await fetch(`${config.apiBaseUrl}/share`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                html: htmlContent,
                expiresIn,
                password,
                sourceWidth: previewSize.sourceWidth,
                sourceHeight: previewSize.sourceHeight,
            }),
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        renderShareResult(data);
        await copyShareDetails();
    }

    function openExportModal(htmlContent) {
        pendingExportHtml = htmlContent;
        exportProgress.hidden = true;
        exportResult.hidden = true;
        exportStartButton.disabled = false;
        exportStartButton.textContent = translations.exportStartRender[currentLang];
        exportModal.classList.add('visible');
    }

    function closeExportModal() {
        exportModal.classList.remove('visible');
        pendingExportHtml = '';
    }

    async function handleExportSubmit(e) {
        e.preventDefault();
        if (!pendingExportHtml) return;

        // Client-side size validation
        const htmlSizeMB = (new Blob([pendingExportHtml]).size / (1024 * 1024)).toFixed(1);
        if (parseFloat(htmlSizeMB) > 3) {
            showWarning(`HTML size (${htmlSizeMB} MB) is large. Consider saving as HTML first, then sharing.`);
        }

        const [width, height] = exportResolution.value.split('x').map(Number);
        const fps = parseInt(exportFps.value);

        exportStartButton.disabled = true;
        exportResult.hidden = true;
        exportProgress.hidden = false;
        exportProgressText.textContent = translations.exportInitializing[currentLang];
        exportProgressPercent.textContent = '0%';
        exportProgressBar.style.width = '0%';

        const durationMatch = pendingExportHtml.match(/<meta\s+name="animation-duration"\s+content="([\d.]+)"/i);
        const durationHint = durationMatch ? parseFloat(durationMatch[1]) : null;

        try {
            const response = await fetch(`${config.apiBaseUrl}/export/video`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    html: pendingExportHtml,
                    width, height, fps,
                    expires_in: exportExpiration.value,
                    duration_seconds: durationHint,
                }),
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let videoId = null;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const jsonStr = line.substring(6);
                    if (jsonStr.includes('[DONE]')) {
                        try {
                            const data = JSON.parse(jsonStr);
                            videoId = data.video_id;
                        } catch (err) { /* ignore */ }
                        break;
                    }
                    try {
                        const data = JSON.parse(jsonStr);
                        if (data.event === 'queued') {
                            exportProgressText.textContent = data.message || '任务排队中...';
                        } else if (data.event === 'started') {
                            exportProgressText.textContent = data.message || '任务开始执行';
                        } else if (data.status && data.percent !== undefined) {
                            exportProgressText.textContent = data.message || translations.exportRendering[currentLang];
                            exportProgressPercent.textContent = `${Math.round(data.percent)}%`;
                            exportProgressBar.style.width = `${Math.round(data.percent)}%`;
                        }
                    } catch (err) { /* skip partial chunks */ }
                }
                if (videoId) break;
            }

            if (videoId) {
                exportProgress.hidden = true;
                exportResult.hidden = false;
                exportDownloadButton.onclick = () => {
                    window.open(`${config.apiBaseUrl}/video/${videoId}`, '_blank');
                };
                window.open(`${config.apiBaseUrl}/video/${videoId}`, '_blank');
                exportStartButton.disabled = false;
                exportStartButton.textContent = translations.exportStartRender[currentLang];
            }
        } catch (error) {
            Logger.error('Video export failed:', error);
            showWarning('Video export failed. Please try again.');
            exportStartButton.disabled = false;
            exportStartButton.textContent = translations.exportStartRender[currentLang];
        }
    }

    function appendAnimationPlayer(htmlContent, topic) {
        Logger.info('Appending animation player:', topic);

        // === 客户端 HTML 后处理增强 ===
        try {
            htmlContent = ZSJPostProcess.enhance(htmlContent, {
                injectCSS: true,
                injectNoise: true,
                injectGSAPPatch: true,
                fixOverflow: true
            });
        } catch (err) {
            Logger.warn('Post-process enhancement failed:', err);
        }

        const node = templates.player.content.cloneNode(true);
        const playerElement = node.firstElementChild;
        playerElement.querySelectorAll('[data-translate-key]').forEach(el => {
            const key = el.dataset.translateKey;
            el.textContent = translations[key]?.[currentLang] || el.textContent;
        });
        const iframe = playerElement.querySelector('.animation-iframe');
        const iframeWrapper = playerElement.querySelector('.iframe-wrapper');
        const previewSize = getPreviewSize();
        if (iframeWrapper) {
            iframeWrapper.style.setProperty('--preview-width', `${previewSize.width}px`);
            iframeWrapper.style.setProperty('--preview-height', `${previewSize.height}px`);
            iframeWrapper.style.setProperty('--source-width', `${previewSize.sourceWidth}px`);
            iframeWrapper.style.setProperty('--source-height', `${previewSize.sourceHeight}px`);
            iframeWrapper.style.setProperty('--preview-scale', previewSize.scale.toString());
        }
        iframe.width = previewSize.sourceWidth;
        iframe.height = previewSize.sourceHeight;
        iframe.style.width = `${previewSize.sourceWidth}px`;
        iframe.style.height = `${previewSize.sourceHeight}px`;
        iframe.srcdoc = htmlContent;

        playerElement.querySelector('.open-new-window').addEventListener('click', () => {
            window.open(createHtmlBlobUrl(htmlContent), '_blank');
        });
        playerElement.querySelector('.save-html').addEventListener('click', () => {
            const url = createHtmlBlobUrl(htmlContent);
            const a = Object.assign(document.createElement('a'), { href: url, download: `${topic.replace(/\s/g, '_') || 'animation'}.html` });
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(url);
            a.remove();
        });
        playerElement.querySelector('.share-html')?.addEventListener('click', () => {
            openShareModal(htmlContent);
        });
        playerElement.querySelector('.export-video')?.addEventListener('click', () => {
            openExportModal(htmlContent);
        });
        chatLog.appendChild(playerElement);
        attachCopyButton(playerElement);
        scrollToBottom();
    }

    function isHtmlContentValid(htmlContent) {
        if (!htmlContent || typeof htmlContent !== 'string') {
            Logger.warn("HTML 内容为空或类型错误");
            return false;
        }

        var trimmed = htmlContent.trim();
        if (trimmed.length < 100) {
            Logger.warn("HTML 内容过短:", trimmed.length, "字符");
            return false;
        }

        // Check for basic HTML document structure
        var hasHtmlTag = /<html[^>]*>/i.test(trimmed);
        var hasBodyTag = /<body[^>]*>/i.test(trimmed);
        var hasClosingHtml = /<\/html>/i.test(trimmed);

        if (!hasHtmlTag && !hasBodyTag) {
            Logger.warn("HTML 缺少 <html> 或 <body> 标签");
            return false;
        }

        if (!hasClosingHtml) {
            Logger.warn("HTML 缺少 </html> 闭合标签");
            // Don't fail on this alone — some browsers can handle it
        }

        // Try DOMParser as additional check
        try {
            var parser = new DOMParser();
            var doc = parser.parseFromString(trimmed, "text/html");
            var parseErrors = doc.querySelectorAll("parsererror");
            if (parseErrors.length > 0) {
                Logger.warn("DOMParser 解析错误:", parseErrors[0].textContent?.substring(0, 200));
                return false;
            }
            if (!doc.body || doc.body.innerHTML.trim() === "") {
                Logger.warn("HTML body 内容为空");
                return false;
            }
        } catch (err) {
            Logger.warn("DOMParser 解析异常:", err.message);
            // Don't fail if DOMParser itself throws — it's very rare
        }

        // Check for GSAP (required for animation)
        var hasGSAP = /gsap/i.test(trimmed);
        if (!hasGSAP) {
            Logger.warn("HTML 中未检测到 GSAP 引用，动画可能不工作");
        }

        return true;
    }

    // ── Two-Stage Generation: Copy → Animation ──

    async function generateCopy(topic) {
        Logger.info('Stage 1: Generating copy for:', topic);
        appendUserMessage(topic);
        const agentThinkingMessage = appendAgentStatus(translations.agentThinking[currentLang]);
        const submitButton = document.querySelector('.submit-button');
        activeGenerationController = new AbortController();
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.classList.add('disabled');
        }
        if (stopGenerationButton) stopGenerationButton.hidden = false;
        accumulatedCode = '';
        const outputElement = appendOutputBlock();

        try {
            const response = await fetch(`${config.apiBaseUrl}/generate/copy`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic: topic, settings: getGenerationSettings() }),
                signal: activeGenerationController.signal
            });
            await consumeCopyResponse(response, topic, agentThinkingMessage, outputElement);
        } catch (error) {
            Logger.error("Copy generation failed:", error);
            if (agentThinkingMessage) agentThinkingMessage.remove();

            let displayMessage = translations.errorFetchFailed[currentLang];
            if (error.name === 'AbortError') {
                displayMessage = translations.generationStopped[currentLang];
            } else if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
                displayMessage = translations.errorFetchFailed[currentLang];
            } else if (error.message.includes('status: 429')) {
                displayMessage = translations.errorTooManyRequests[currentLang];
            } else if (error instanceof LLMParseError) {
                displayMessage = translations.errorLLMParseError[currentLang];
            }

            showWarning(displayMessage);
            appendErrorMessage(translations.errorMessage[currentLang], error);
            if (outputElement) markOutputAsComplete(outputElement);
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.classList.remove('disabled');
            }
            if (stopGenerationButton) stopGenerationButton.hidden = true;
            activeGenerationController = null;
        }
    }

    async function consumeCopyResponse(response, displayTopic, agentThinkingMessage, outputElement) {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullResponse = '';
        let queueWarningVisible = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;

                const jsonStr = line.substring(6);
                if (jsonStr.includes('[DONE]')) {
                    conversationHistory.push({ role: 'assistant', content: fullResponse });
                    markOutputAsComplete(outputElement);

                    // Parse the accumulated JSON
                    let copyJson = null;
                    try {
                        // Try to extract JSON from the response (handle possible markdown wrapping)
                        let jsonText = fullResponse;
                        const jsonMatch = fullResponse.match(/```(?:json)?\s*([\s\S]*?)```/);
                        if (jsonMatch) jsonText = jsonMatch[1];
                        // Find the outermost { ... }
                        const braceStart = jsonText.indexOf('{');
                        const braceEnd = jsonText.lastIndexOf('}');
                        if (braceStart !== -1 && braceEnd > braceStart) {
                            jsonText = jsonText.substring(braceStart, braceEnd + 1);
                        }
                        copyJson = JSON.parse(jsonText);
                    } catch (err) {
                        Logger.error('Failed to parse copy JSON:', err, 'Raw (first 200 chars):', fullResponse.substring(0, 200));
                        appendRetryPrompt(displayTopic);
                        scrollToBottom();
                        return;
                    }

                    if (!copyJson || !copyJson.acts || !copyJson.acts.length) {
                        Logger.warn('Invalid copy JSON structure:', copyJson);
                        appendRetryPrompt(displayTopic);
                        scrollToBottom();
                        return;
                    }

                    currentCopyJson = copyJson;
                    appendCopyReview(copyJson, displayTopic);
                    scrollToBottom();
                    return;
                }

                let data;
                try {
                    data = JSON.parse(jsonStr);
                } catch (err) {
                    Logger.error('Failed to parse JSON:', jsonStr.substring(0, 200));
                    throw new LLMParseError('Invalid response format from server.');
                }

                if (data.event === 'queued') {
                    queueWarningVisible = true;
                    showWarning(translations.generationQueued[currentLang], {
                        persistent: true,
                        blocking: true,
                        loading: true,
                        cancelable: true,
                        cancelText: translations.cancelQueuedTask[currentLang],
                    });
                    continue;
                }

                if (data.event === 'started') {
                    if (queueWarningVisible) {
                        forceHideWarning();
                        showWarning(translations.generationStarted[currentLang]);
                        queueWarningVisible = false;
                    }
                    continue;
                }

                if (data.event === 'reset') {
                    fullResponse = '';
                    if (outputElement) {
                        const codeEl = outputElement.querySelector('code');
                        if (codeEl) codeEl.innerHTML = '';
                    }
                    continue;
                }

                if (data.error) throw new LLMParseError(data.error);

                const token = data.token || '';
                if (agentThinkingMessage) agentThinkingMessage.remove();
                fullResponse += token;
                updateOutputBlock(outputElement, token);
            }
        }
    }

    function appendCopyReview(copyJson, topic) {
        const node = templates['copy-review']?.content?.cloneNode(true);
        if (!node) {
            Logger.error('copy-review template not found');
            return;
        }
        const element = node.firstElementChild;
        copyReviewElement = element;

        // Update header
        const titleEl = element.querySelector('.copy-title');
        if (titleEl) titleEl.textContent = copyJson.title || topic;

        const narrativeTypeEl = element.querySelector('.copy-narrative-type');
        if (narrativeTypeEl) {
            const typeMap = { problem_conflict: '问题冲突型' };
            narrativeTypeEl.textContent = typeMap[copyJson.narrative_type] || copyJson.narrative_type || '';
        }

        const durationEl = element.querySelector('.copy-duration');
        if (durationEl) durationEl.textContent = `约 ${copyJson.total_duration_hint || 60} 秒`;

        // Build act cards
        const actsContainer = element.querySelector('.acts-container');
        if (actsContainer && copyJson.acts) {
            const actNames = ['认知爆破', '延迟满足', '层层揭秘', '高潮揭晓', '记忆钉'];
            const actIcons = ['💥', '🔮', '🔍', '💡', '📌'];

            copyJson.acts.forEach((act, index) => {
                const card = document.createElement('div');
                card.className = 'act-card';
                card.dataset.actIndex = index;
                card.innerHTML = `
                    <div class="act-card-header">
                        <span class="act-number">${actIcons[index] || '▶'} 第${act.act || index + 1}幕</span>
                        <span class="act-name">${act.name || actNames[index] || ''}</span>
                        <span class="act-goal">${act.goal || ''}</span>
                        <span class="act-duration-hint">~${act.duration_hint || 0}s</span>
                    </div>
                    <div class="act-card-body">
                        <div class="act-field">
                            <label>手法</label>
                            <span class="act-method" data-field="method_used">${act.method_used || ''}</span>
                        </div>
                        <div class="act-field">
                            <label>旁白（中文）</label>
                            <span class="act-narration" data-field="narration">${act.narration || ''}</span>
                        </div>
                        <div class="act-field">
                            <label>旁白（英文）</label>
                            <span class="act-narration-en" data-field="narration_en">${act.narration_en || ''}</span>
                        </div>
                        <div class="act-field">
                            <label>画面描述</label>
                            <span class="act-visual" data-field="visual_description">${act.visual_description || ''}</span>
                        </div>
                        <div class="act-field">
                            <label>画面大字</label>
                            <span class="act-on-screen" data-field="on_screen_text">${act.on_screen_text || ''}</span>
                        </div>
                    </div>
                `;
                actsContainer.appendChild(card);
            });
        }

        // Wire up buttons
        const editButton = element.querySelector('.copy-edit-toggle');
        if (editButton) {
            editButton.addEventListener('click', () => toggleCopyEdit());
        }

        const regenerateButton = element.querySelector('.copy-regenerate');
        if (regenerateButton) {
            regenerateButton.addEventListener('click', () => {
                element.remove();
                copyReviewElement = null;
                currentCopyJson = null;
                generateCopy(topic);
            });
        }

        const generateAnimButton = element.querySelector('.copy-generate-animation');
        if (generateAnimButton) {
            generateAnimButton.addEventListener('click', () => {
                const editedCopy = isCopyEditing ? exportEditedCopy() : currentCopyJson;
                if (editedCopy) {
                    currentCopyJson = editedCopy;
                    generateAnimationFromCopy(editedCopy);
                }
            });
        }

        chatLog.appendChild(element);
        attachCopyButton(element);
        scrollToBottom();
    }

    function toggleCopyEdit() {
        if (!copyReviewElement) return;

        isCopyEditing = !isCopyEditing;
        const editButton = copyReviewElement.querySelector('.copy-edit-toggle span');
        const allFields = copyReviewElement.querySelectorAll('.act-card-body span[data-field]');

        if (isCopyEditing) {
            if (editButton) editButton.textContent = '完成编辑';
            copyReviewElement.classList.add('is-editing');
            // Convert spans to inputs/textareas
            allFields.forEach(span => {
                const field = span.dataset.field;
                const value = span.textContent;
                const isLong = field === 'visual_description' || field === 'narration' || field === 'narration_en';
                const input = document.createElement(isLong ? 'textarea' : 'input');
                input.type = isLong ? undefined : 'text';
                input.value = value;
                input.dataset.field = field;
                input.className = 'act-edit-field';
                if (isLong) input.rows = 3;
                span.replaceWith(input);
            });
        } else {
            if (editButton) editButton.textContent = '编辑文案';
            copyReviewElement.classList.remove('is-editing');
            // Convert inputs back to spans
            const allInputs = copyReviewElement.querySelectorAll('.act-edit-field');
            allInputs.forEach(input => {
                const field = input.dataset.field;
                const value = input.value;
                const span = document.createElement('span');
                span.textContent = value;
                span.dataset.field = field;
                span.className = `act-${field}`;
                input.replaceWith(span);
            });
        }
    }

    function exportEditedCopy() {
        if (!copyReviewElement || !currentCopyJson) return null;

        const editedCopy = JSON.parse(JSON.stringify(currentCopyJson)); // Deep clone

        const actCards = copyReviewElement.querySelectorAll('.act-card');
        actCards.forEach((card, index) => {
            if (index >= editedCopy.acts.length) return;
            const act = editedCopy.acts[index];

            const methodEl = card.querySelector('[data-field="method_used"]');
            if (methodEl) act.method_used = methodEl.textContent || methodEl.value || '';

            const narrationEl = card.querySelector('[data-field="narration"]');
            if (narrationEl) act.narration = narrationEl.textContent || narrationEl.value || '';

            const narrationEnEl = card.querySelector('[data-field="narration_en"]');
            if (narrationEnEl) act.narration_en = narrationEnEl.textContent || narrationEnEl.value || '';

            const visualEl = card.querySelector('[data-field="visual_description"]');
            if (visualEl) act.visual_description = visualEl.textContent || visualEl.value || '';

            const onScreenEl = card.querySelector('[data-field="on_screen_text"]');
            if (onScreenEl) act.on_screen_text = onScreenEl.textContent || onScreenEl.value || '';
        });

        return editedCopy;
    }

    async function generateAnimationFromCopy(copyJson) {
        Logger.info('Stage 2: Generating animation from copy');
        const agentThinkingMessage = appendAgentStatus(translations.agentThinking[currentLang]);
        const submitButton = document.querySelector('.submit-button');
        activeGenerationController = new AbortController();
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.classList.add('disabled');
        }
        if (stopGenerationButton) stopGenerationButton.hidden = false;
        accumulatedCode = '';
        const outputElement = appendOutputBlock();

        try {
            const response = await fetch(`${config.apiBaseUrl}/generate/animation`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ copy_json: copyJson, settings: getGenerationSettings() }),
                signal: activeGenerationController.signal
            });
            // Reuse the same SSE consumer from the original flow
            await consumeGenerationResponse(response, copyJson.title || '动画', agentThinkingMessage, outputElement);
        } catch (error) {
            Logger.error("Animation from copy failed:", error);
            if (agentThinkingMessage) agentThinkingMessage.remove();

            let displayMessage = translations.errorFetchFailed[currentLang];
            if (error.name === 'AbortError') {
                displayMessage = translations.generationStopped[currentLang];
            } else if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
                displayMessage = translations.errorFetchFailed[currentLang];
            } else if (error.message.includes('status: 429')) {
                displayMessage = translations.errorTooManyRequests[currentLang];
            } else if (error instanceof LLMParseError) {
                displayMessage = translations.errorLLMParseError[currentLang];
            }

            showWarning(displayMessage);
            appendErrorMessage(translations.errorMessage[currentLang], error);
            if (outputElement) markOutputAsComplete(outputElement);
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.classList.remove('disabled');
            }
            if (stopGenerationButton) stopGenerationButton.hidden = true;
            activeGenerationController = null;
        }
    }

    const scrollToBottom = () => chatLog.scrollTo({ top: chatLog.scrollHeight, behavior: 'smooth' });

    function setNextPlaceholder() {
        const placeholderTexts = translations.placeholders[currentLang];
        const newSpan = document.createElement('span');
        newSpan.textContent = placeholderTexts[placeholderIndex];
        placeholderContainer.innerHTML = '';
        placeholderContainer.appendChild(newSpan);
        placeholderIndex = (placeholderIndex + 1) % placeholderTexts.length;
    }

    function startPlaceholderAnimation() {
        if (placeholderInterval) clearInterval(placeholderInterval);
        const placeholderTexts = translations.placeholders[currentLang];
        if (placeholderTexts && placeholderTexts.length > 0) {
            placeholderIndex = 0;
            setNextPlaceholder();
            placeholderInterval = setInterval(setNextPlaceholder, 4000);
        }
    }

    function setLanguage(lang) {
        if (!['zh', 'en'].includes(lang)) return;
        currentLang = lang;
        document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
        document.querySelectorAll('[data-translate-key]').forEach(el => {
            const key = el.dataset.translateKey;
            const translation = translations[key]?.[lang];
            if (!translation) return;
            if (el.hasAttribute('placeholder')) el.placeholder = translation;
            else if (el.hasAttribute('title')) el.title = translation;
            else el.textContent = translation;
        });
        languageSwitcher?.querySelectorAll('button').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.lang === lang);
        });
        startPlaceholderAnimation();
        localStorage.setItem('preferredLanguage', lang);
    }

    let placeholderIndex = 0;

    function init() {
        initialInput.addEventListener('input', () => {
            placeholderContainer.classList.toggle('hidden', initialInput.value.length > 0);
        });
        initialInput.addEventListener('focus', () => clearInterval(placeholderInterval));
        initialInput.addEventListener('blur', () => {
            if (initialInput.value.length === 0) startPlaceholderAnimation();
        });

        initialForm.addEventListener('submit', handleFormSubmit);
        paperExplainButton?.addEventListener('click', openPaperUploadModal);
        paperUploadClose?.addEventListener('click', closePaperUploadModal);
        paperUploadModal?.addEventListener('click', (e) => {
            if (e.target === paperUploadModal) closePaperUploadModal();
        });
        paperUploadForm?.addEventListener('submit', handlePaperUploadSubmit);
        paperFileInput?.addEventListener('change', updatePaperFileName);
        passphraseForm?.addEventListener('submit', handlePassphraseSubmit);
        initPassphraseGate();
        chatForm.addEventListener('submit', handleFormSubmit);
        newChatButton.addEventListener('click', () => location.reload());
        stopGenerationButton?.addEventListener('click', () => {
            activeGenerationController?.abort();
        });
        queueCancelButton?.addEventListener('click', () => {
            activeGenerationController?.abort();
        });
        settingsToggles.forEach(button => {
            button.addEventListener('click', () => openSettingsPanel(false));
        });
        settingsClose.addEventListener('click', closeSettingsPanel);
        settingsPanel.addEventListener('click', (e) => {
            if (e.target === settingsPanel) closeSettingsPanel();
        });
        settingsConfirm.addEventListener('click', confirmGenerationFromSettings);
        previewConfirmClose?.addEventListener('click', () => resolvePreviewConfirm(false));
        previewConfirmCancel?.addEventListener('click', () => resolvePreviewConfirm(false));
        previewConfirmContinue?.addEventListener('click', () => resolvePreviewConfirm(true));
        previewConfirmModal?.addEventListener('click', (e) => {
            if (e.target === previewConfirmModal) resolvePreviewConfirm(false);
        });
        languageSwitcher?.addEventListener('click', (e) => {
            const target = e.target.closest('button');
            if (target) setLanguage(target.dataset.lang);
        });

        function hideModal() {
            featureModal.classList.remove('visible');
        }

        modalCloseButton.addEventListener('click', hideModal);
        featureModal.addEventListener('click', (e) => {
            if (e.target === featureModal) hideModal();
        });
        shareModalCloseButton?.addEventListener('click', closeShareModal);
        shareModal?.addEventListener('click', (e) => {
            if (e.target === shareModal) closeShareModal();
        });
        shareForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (latestShareDetails) {
                await copyShareDetails();
                return;
            }
            const password = sharePassword.value.trim();
            if (!/^\d{4,20}$/.test(password)) {
                showWarning(translations.sharePasswordRequired[currentLang]);
                sharePassword.focus();
                return;
            }
            try {
                await shareHtmlLink(pendingShareHtml, shareExpiration.value, password, getPreviewSize());
            } catch (error) {
                Logger.error('Failed to create share link:', error);
                showWarning(translations.shareFailed[currentLang]);
            }
        });

        modalGitHubButton.addEventListener('click', () => {
            window.open('https://github.com/ZhaoShiJiu/Animation', '_blank');
            hideModal();
        });

        exportModalClose?.addEventListener('click', closeExportModal);
        exportModal?.addEventListener('click', (e) => {
            if (e.target === exportModal) closeExportModal();
        });
        exportForm?.addEventListener('submit', handleExportSubmit);

        const savedLang = localStorage.getItem('preferredLanguage');
        const browserLang = navigator.language?.toLowerCase() || ''; // e.g. 'zh-cn'

        let initialLang = 'en'; 
        if (['zh', 'en'].includes(savedLang)) {
            initialLang = savedLang;
        } else if (browserLang.startsWith('zh')) {
            initialLang = 'zh';
        } else if (browserLang.startsWith('en')) {
            initialLang = 'en';
        }

        setLanguage(initialLang);
        showMobileUnsupportedWarning();
        loadOneQuotes();
    }

    init();
});

function showWarning(message, options = {}) {
    const box = document.getElementById('warning-box');
    const overlay = document.getElementById('overlay');
    const text = document.getElementById('warning-message');
    const description = document.getElementById('warning-description');
    const spinner = document.getElementById('warning-spinner');
    const closeButton = document.getElementById('warning-close-button');
    const cancelButton = document.getElementById('queue-cancel-button');

    text.textContent = message;
    if (cancelButton) {
        cancelButton.textContent = options.cancelText || '取消任务';
        cancelButton.hidden = !options.cancelable;
    }
    if (description) {
        description.textContent = options.description || '';
        description.hidden = !options.description;
    }
    if (spinner) spinner.hidden = !options.loading;
    if (closeButton) closeButton.hidden = Boolean(options.blocking);
    box.classList.toggle('is-blocking', Boolean(options.blocking));
    box.classList.toggle('has-description', Boolean(options.description));
    box.style.display = 'flex';
    overlay.style.display = 'block';

    if (window.warningTimer) clearTimeout(window.warningTimer);
    if (options.persistent) return;

    window.warningTimer = setTimeout(() => {
        hideWarning();
    }, 10000);
}

function hideWarning() {
    const box = document.getElementById('warning-box');
    if (box?.classList.contains('is-blocking')) return;
    forceHideWarning();
}

function forceHideWarning() {
    if (window.warningTimer) {
        clearTimeout(window.warningTimer);
        window.warningTimer = null;
    }
    const box = document.getElementById('warning-box');
    const overlay = document.getElementById('overlay');
    const spinner = document.getElementById('warning-spinner');
    const description = document.getElementById('warning-description');
    const closeButton = document.getElementById('warning-close-button');
    const cancelButton = document.getElementById('queue-cancel-button');
    box?.classList.remove('is-blocking', 'has-description');
    if (spinner) spinner.hidden = true;
    if (description) {
        description.hidden = true;
        description.textContent = '';
    }
    if (closeButton) closeButton.hidden = false;
    if (cancelButton) cancelButton.hidden = true;
    box.style.display = 'none';
    overlay.style.display = 'none';
}
