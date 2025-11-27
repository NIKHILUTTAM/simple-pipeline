pipeline {
  agent any

  options {
    timestamps()
    // ansiColor('xterm') // Commented out to fix "Invalid option type" error if plugin is missing
  }

  environment {
    REPO = 'https://github.com/NIKHILUTTAM/simple-pipeline.git'
    BRANCH = 'main'
    // SIMULATE_FAILURE can be toggled to false to run the real build
    SIMULATE_FAILURE = 'true' 
  }

  stages {
    stage('Clean Workspace') {
      steps {
        echo "Cleaning workspace..."
        // Safe delete for Windows
        bat 'if exist .git rmdir /s /q .git'
      }
    }

    stage('Checkout') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'github-token', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_PSW')]) {
          bat """
            git init
            git remote add origin ${REPO}
            set GIT_ASKPASS=echo
            git fetch --no-tags --progress https://%GIT_USER%:%GIT_PSW%@github.com/%GIT_USER%/simple-pipeline.git +refs/heads/${BRANCH}:refs/remotes/origin/${BRANCH}
            git checkout -f origin/${BRANCH}
          """
        }
      }
    }

    stage('Run Tests / Build') {
      steps {
        script {
          env.BUILD_FAILED = 'false'
          echo "Running tests/build..."
          
          // Simulation logic for Windows
          def rc = bat(returnStatus: true, script: '''
            if "%SIMULATE_FAILURE%"=="false" (
                echo Running real build
                exit /b 0
            ) else (
                echo Simulated failure
                exit /b 1
            )
          ''')
          
          if (rc != 0) {
            echo "⚠ Build failed (exit code ${rc}). Initiating Auto-Heal."
            env.BUILD_FAILED = 'true'
          } else {
            echo "✅ Build succeeded."
          }
        }
      }
    }

    stage('AI Diagnosis & Patch') {
      when {
        expression { env.BUILD_FAILED == 'true' }
      }
      steps {
        withCredentials([string(credentialsId: 'gemini-key', variable: 'GEMINI_KEY')]) {
          script {
            // 1. Prepare Prompt
            // We ask for a unified diff specifically
            def prompt = '''
You are a DevOps Auto-Healer.
The build failed. Please generate a git patch to fix the code.
Output ONLY a JSON object with a "patch" field containing the unified diff.
Example: { "patch": "diff --git a/index.html b/index.html\\n..." }
'''
            // Write prompt to file to avoid quoting issues in PowerShell
            writeFile file: 'prompt.txt', text: prompt

            // 2. Call Gemini API using PowerShell with Error Handling
            powershell '''
$ErrorActionPreference = "Stop"
$apiKey = $env:GEMINI_KEY
# Sanitize API Key (remove spaces/newlines)
if ($apiKey) { $apiKey = $apiKey.Trim() }

$promptText = Get-Content prompt.txt -Raw

$bodyObj = @{
    "contents" = @(
        @{
            "parts" = @(
                @{ "text" = $promptText }
            )
        }
    )
}
# Convert to JSON
$bodyJson = $bodyObj | ConvertTo-Json -Depth 10 -Compress

$uri = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$apiKey"

Write-Host "Calling Gemini API..."

try {
    # Force UTF-8 Encoding for the body
    $utf8Body = [System.Text.Encoding]::UTF8.GetBytes($bodyJson)
    
    $response = Invoke-RestMethod -Method Post -Uri $uri -ContentType "application/json; charset=utf-8" -Body $utf8Body
    $response | ConvertTo-Json -Depth 10 | Out-File response.json -Encoding utf8
} catch {
    Write-Host "❌ HTTP Request Failed"
    $e = $_.Exception
    # Check if there is a response body (e.g. from Google)
    if ($e.Response) {
        $reader = New-Object System.IO.StreamReader($e.Response.GetResponseStream())
        $errBody = $reader.ReadToEnd()
        Write-Host "⬇️ Gemini Error Response ⬇️"
        Write-Host $errBody
        Write-Host "⬆️ -------------------- ⬆️"
    }
    throw $_
}
'''
          }
        }
      }
    }

    stage('Extract & Apply Patch') {
      when {
        expression { env.BUILD_FAILED == 'true' }
      }
      steps {
        script {
          // 3. Parse JSON and Apply Patch
          powershell '''
$ErrorActionPreference = "Stop"

if (-not (Test-Path response.json)) { Write-Error "No response from AI"; exit 1 }

$json = Get-Content response.json -Raw | ConvertFrom-Json
$aiText = $json.candidates[0].content.parts[0].text

# Extract JSON from Markdown if present
if ($aiText -match "```json([\\s\\S]*?)```") {
    $aiText = $matches[1]
}

try {
    $patchJson = $aiText | ConvertFrom-Json
    $patchContent = $patchJson.patch
    
    if (-not $patchContent) { throw "No patch field in AI response" }
    
    $patchContent | Out-File -FilePath autoheal_patch.diff -Encoding utf8
    Write-Host "✅ Patch saved to autoheal_patch.diff"
} catch {
    Write-Warning "Could not parse AI response as JSON. Dump: $aiText"
    exit 1
}

# Apply
Write-Host "Applying patch..."
git apply --ignore-space-change --ignore-whitespace autoheal_patch.diff
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Patch applied successfully!"
} else {
    Write-Error "❌ Git apply failed."
    exit 1
}
'''
        }
      }
    }

    stage('Commit & Push Fix') {
      when {
        expression { env.BUILD_FAILED == 'true' }
      }
      steps {
        withCredentials([usernamePassword(credentialsId: 'github-token', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_PSW')]) {
          bat """
            git config user.email "jenkins-bot@autoheal"
            git config user.name "Jenkins Bot"
            git add .
            git commit -m "🚑 Auto-Heal: AI fixed build failure"
            git push https://%GIT_USER%:%GIT_PSW%@github.com/%GIT_USER%/simple-pipeline.git HEAD:${BRANCH}
          """
        }
      }
    }
    
    stage('Trigger Deployment') {
       when {
         expression { env.BUILD_FAILED == 'true' }
       }
       steps {
         withCredentials([string(credentialsId: 'vercel-token', variable: 'VERCEL_TOKEN')]) {
           powershell '''
             if (Get-Command vercel -ErrorAction SilentlyContinue) {
               echo "Deploying to Vercel..."
               vercel --prod --confirm --token $env:VERCEL_TOKEN
             } else {
               echo "Vercel CLI not found. Skipping deployment."
             }
           '''
         }
       }
    }
  }

  post {
    always {
      archiveArtifacts artifacts: 'response.json, autoheal_patch.diff', allowEmptyArchive: true
    }
  }
}