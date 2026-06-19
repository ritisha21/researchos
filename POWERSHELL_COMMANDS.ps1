# =============================================================================
# ResearchOS — Windows PowerShell Testing Guide (All 5 Phases)
# =============================================================================
# PowerShell's `curl` = Invoke-WebRequest. Use commands below instead.
# EASIEST OPTION: open http://localhost:8000/docs in your browser (Swagger UI)
# =============================================================================


# ── HEALTH ───────────────────────────────────────────────────────────────────
Invoke-RestMethod -Uri "http://localhost:8000/health"
Invoke-RestMethod -Uri "http://localhost:8000/health/ready"


# =============================================================================
# PHASE 1 — ROADMAP GENERATION
# =============================================================================

$body = @{ topic = "Computer Vision"; force_refresh = $false } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/roadmap" `
    -Method POST -Body $body -ContentType "application/json"

$body = @{ topic = "Reinforcement Learning" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/roadmap" `
    -Method POST -Body $body -ContentType "application/json"

$body = @{ topic = "Graph Neural Networks" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/roadmap" `
    -Method POST -Body $body -ContentType "application/json"


# =============================================================================
# PHASE 2 — PAPER SEARCH
# =============================================================================

# Quick GET
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/papers/search?q=ResNet&limit=5"
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/papers/search?q=transformer&limit=10&sort_by=citation_count"

# POST — both sources, sorted by citations
$body = @{
    query        = "attention is all you need"
    limit        = 10
    sources      = @("semantic_scholar", "arxiv")
    sort_by      = "citation_count"
    save_results = $true
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/papers/search" `
    -Method POST -Body $body -ContentType "application/json"

# arXiv only
$body = @{ query = "federated learning"; limit = 5; sources = @("arxiv") } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/papers/search" `
    -Method POST -Body $body -ContentType "application/json"

# Get saved paper by UUID
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/papers/PASTE-UUID-HERE"


# =============================================================================
# PHASE 3 — AI ANALYSIS
# =============================================================================

# --- Summarise ---
$body = @{
    title         = "Deep Residual Learning for Image Recognition"
    abstract      = "We present a residual learning framework to ease training of deep networks. We explicitly reformulate the layers as learning residual functions with reference to the layer inputs."
    force_refresh = $false
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/papers/summarise" `
    -Method POST -Body $body -ContentType "application/json"

# Title only (no abstract)
$body = @{ title = "Attention Is All You Need" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/papers/summarise" `
    -Method POST -Body $body -ContentType "application/json"

# --- Explain (beginner-friendly) ---
$body = @{
    title    = "BERT: Pre-training of Deep Bidirectional Transformers"
    abstract = "We introduce BERT, a language representation model designed to pre-train deep bidirectional representations from unlabeled text."
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/papers/explain" `
    -Method POST -Body $body -ContentType "application/json"

# --- Notes ---
$body = @{ title = "Generative Adversarial Networks" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/papers/notes" `
    -Method POST -Body $body -ContentType "application/json"

# --- Takeaways ---
$body = @{ title = "Dropout: A Simple Way to Prevent Neural Networks from Overfitting" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/papers/takeaways" `
    -Method POST -Body $body -ContentType "application/json"

# --- Literature Review ---
$body = @{
    titles = @(
        "Attention Is All You Need",
        "BERT: Pre-training of Deep Bidirectional Transformers",
        "GPT-3: Language Models are Few-Shot Learners"
    )
    focus  = "compare how each paper advances language model pre-training"
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/papers/literature-review" `
    -Method POST -Body $body -ContentType "application/json"


# =============================================================================
# PHASE 4 — PDF UPLOAD
# =============================================================================

# Upload a PDF file (replace path with your actual PDF)
$pdfPath  = "C:\Users\KIIT\Downloads\resnet_paper.pdf"
$pdfBytes = [System.IO.File]::ReadAllBytes($pdfPath)
$boundary = [System.Guid]::NewGuid().ToString()
$encoding = [System.Text.Encoding]::UTF8

$bodyLines = @(
    "--$boundary",
    'Content-Disposition: form-data; name="title"',
    "",
    "Deep Residual Learning for Image Recognition",
    "--$boundary",
    'Content-Disposition: form-data; name="authors"',
    "",
    "Kaiming He, Xiangyu Zhang, Shaoqing Ren, Jian Sun",
    "--$boundary",
    'Content-Disposition: form-data; name="year"',
    "",
    "2016",
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"resnet.pdf`"",
    "Content-Type: application/pdf",
    "",
    ""
)

$bodyBytes  = $encoding.GetBytes(($bodyLines -join "`r`n"))
$closingBytes = $encoding.GetBytes("`r`n--$boundary--`r`n")
$fullBody   = $bodyBytes + $pdfBytes + $closingBytes

$response = Invoke-RestMethod `
    -Uri         "http://localhost:8000/api/v1/upload" `
    -Method      POST `
    -Body        $fullBody `
    -ContentType "multipart/form-data; boundary=$boundary"

$response
# Save the paper_id for Phase 5:
$paperId = $response.paper_id
Write-Host "Paper ID: $paperId"


# =============================================================================
# PHASE 5 — PAPER CHAT WITH CITATIONS
# =============================================================================

# Replace paper_id with the value from Phase 4 upload response
$paperId = "PASTE-PAPER-ID-FROM-UPLOAD-HERE"

# Single question
$body = @{
    paper_id = $paperId
    question = "What are the key contributions of this paper?"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/chat" `
    -Method POST -Body $body -ContentType "application/json"

# Multi-turn conversation
$body = @{
    paper_id = $paperId
    question = "What limitations does the paper mention?"
    conversation_history = @(
        @{ role = "user";      content = "What are the key contributions?" },
        @{ role = "assistant"; content = "The paper introduces residual connections..." }
    )
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/chat" `
    -Method POST -Body $body -ContentType "application/json"

# More questions to try:
# "Explain the architecture in simple terms"
# "What datasets were used for evaluation?"
# "How does this compare to VGG networks?"
# "What is the significance of skip connections?"


# =============================================================================
# UTILITIES
# =============================================================================

# Pretty-print any response
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/papers/search?q=ResNet&limit=3" |
    ConvertTo-Json -Depth 10

# Open Swagger UI (recommended — easier than PowerShell)
Start-Process "http://localhost:8000/docs"

# Check all routes
Invoke-RestMethod -Uri "http://localhost:8000/openapi.json" | ConvertTo-Json -Depth 3
