pipeline {
  agent any

  // Do NOT interpolate secrets in Groovy strings; we'll use withCredentials to expose env vars safely
  options {
    timestamps()
    ansiColor('xterm')
  }

  environment {
    REPO = 'https://github.com/NIKHILUTTAM/simple-pipeline.git'
    BRANCH = 'main'
    // These are placeholders — real values come from withCredentials in the steps
  }

  stages {
    stage('Declarative: Checkout SCM') {
      steps {
        echo "Preparing workspace..."
        // Clean workspace, then the normal git checkout below inside credentials block
      }
    }

    stage('Checkout') {
      steps {
        // Use the credential entry stored in Jenkins (username/password or token)
        withCredentials([usernamePassword(credentialsId: 'github-token', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_PSW')]) {
          bat """
            if exist .git rmdir /s /q .git
            git init
            git remote add origin ${REPO}
            set GIT_ASKPASS=echo
            git fetch --no-tags --progress https://%GIT_USER%:%GIT_PSW%@github.com/%GIT_USER%/simple-pipeline.git +refs/heads/${BRANCH}:refs/remotes/origin/${BRANCH}
            git checkout -f origin/${BRANCH}
            git status --porcelain
          """
        }
      }
    }

    stage('Run Tests / Build') {
      steps {
        script {
          // Soft-fail: capture return code and don't abort pipeline
          env.BUILD_FAILED = 'false'
          echo "Running tests/build (set SIMULATE_FAILURE=false to run your real build)..."
          // Example: run your test script here. For demo/testing we simulate a failure; replace with real build command
          def rc = bat(returnStatus: true, script: 'if "%SIMULATE_FAILURE%"=="false" (echo Running real build && exit /b 0) else (echo Simulated failure && exit /b 1)')
          if (rc != 0) {
            echo "⚠ Build failed (exit code ${rc}). Continuing to auto-heal stage."
            env.BUILD_FAILED = 'true'
          } else {
            echo "✅ Build succeeded."
          }
        }
      }
    }

    stage('Call Gemini to generate patch') {
      when {
        expression { env.BUILD_FAILED == 'true' }
      }
      steps {
        // Use secret text bindings — avoid Groovy interpolation of secrets.
        withCredentials([
          string(credentialsId: 'gemini-key', variable: 'GEMINI_KEY')
        ]) {
          // Remove old artifacts
          bat 'if exist response.json del /f /q response.json'
          bat 'if exist autoheal_patch.diff del /f /q autoheal_patch.diff'
          // Call Gemini (PowerShell here-string used to build request body cleanly)
          powershell(
'''$ErrorActionPreference = "Stop"

# Build prompt: ask Gemini to output ONLY JSON with fields "summary" and "patch"
$prompt = @'
You are an assistant that generates a tiny safe patch for a web repo.
Output only JSON, with two fields:
  "summary": short explanation
  "patch": the unified diff text (a plain string) that can be applied with git apply.
Keep changes minimal and safe. If you cannot produce a patch, respond with {"summary":"no-patch","patch":""}.
Patch should be a standard unified diff for files modified (e.g. "diff --git a/index.html b/index.html\n--- a/index.html\n+++ b/index.html\n@@ ...").
'@

$body = @{
  "prompt" = $prompt
  "instructions" = "Produce JSON only. Include fields summary and patch."
} | ConvertTo-Json -Depth 10

# Use curl (Windows 10+ has curl) - we post to the Generative Language REST endpoint
$uri = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=$env:GEMINI_KEY"

# Using curl here for simplicity. Save raw output to response.json
$curlArgs = @(
  '-s', '-X', 'POST', $uri,
  '-H', 'Content-Type: application/json',
  '-d', $body
)
Write-Host "Calling Gemini API..."
# run curl
$proc = Start-Process -FilePath curl -ArgumentList $curlArgs -NoNewWindow -Wait -PassThru -RedirectStandardOutput response.json
if ($proc.ExitCode -ne 0) {
  Write-Host "curl returned exit code $($proc.ExitCode)."
  exit 1
}
Write-Host "Gemini response saved to response.json"
'''
          )
        }
      }
    }

    stage('Extract & Validate Patch') {
      when {
        expression { env.BUILD_FAILED == 'true' }
      }
      steps {
        script {
          // Try to parse response.json and extract patch; run in PowerShell to handle JSON robustly
          powershell '''
$ErrorActionPreference = "Stop"
if (-not (Test-Path response.json)) { Write-Host "response.json missing"; exit 2 }

# Try to parse common response shapes. We'll attempt multiple paths.
$content = Get-Content response.json -Raw
# If the body itself is a JSON with fields patch or contains a text field
$patch = ""
try {
  $j = $null
  try { $j = $content | ConvertFrom-Json } catch { $j = $null }
  if ($j -ne $null) {
    # look for common keys
    if ($j.patch) { $patch = $j.patch }
    elseif ($j.output -and $j.output[0] -and $j.output[0].content) {
      # vendor-specific: try to find patch inside outputs
      $patch = ($j.output[0].content | Out-String)
    } elseif ($j.response) {
      $patch = ($j.response | Out-String)
    } elseif ($j.candidates -and $j.candidates[0] -and $j.candidates[0].content) {
      $patch = ($j.candidates[0].content | Out-String)
    } else {
      # attempt to find a JSON blob inside text
      $text = $content -join "`n"
      $maybe = ($text | Select-String -Pattern '\{.*"patch".*' -SimpleMatch -AllMatches)
      if ($maybe) { $patch = $maybe.Matches.Value -join "`n" }
    }
  } else {
    # not JSON — maybe raw text, so use full content
    $patch = $content
  }
} catch {
  Write-Host "Failed to parse response.json: $_"
  exit 3
}

# Heuristic: look for unified diff markers; if not found, leave patch empty
if (-not ($patch -match 'diff --git|^--- a/|^\+\+\+ b/')) {
  Write-Host "No unified-diff detected in Gemini output. Saving raw content to response_body.txt"
  $content | Out-File -Encoding utf8 response_body.txt
  exit 4
}

# Save patch file
$patch | Out-File -Encoding utf8 autoheal_patch.diff
Write-Host "Saved patch to autoheal_patch.diff"
'''
        }
      }
    }

    stage('Apply Patch (real code edits)') {
      when {
        expression { env.BUILD_FAILED == 'true' }
      }
      steps {
        script {
          // Try apply; if fails, fallback to safe simulated fix
          def applyRc = powershell(returnStatus: true, script: '''
$ErrorActionPreference = "Stop"
if (-not (Test-Path autoheal_patch.diff)) { Write-Host "No patch present"; exit 2 }
# Validate patch
git apply --check autoheal_patch.diff
if ($LASTEXITCODE -ne 0) { Write-Host "git apply --check failed"; exit 3 }

# Apply patch to index (create working changes)
git apply autoheal_patch.diff
if ($LASTEXITCODE -ne 0) { Write-Host "git apply failed"; exit 4 }
Write-Host "Patch applied successfully"
exit 0
''')
          if (applyRc == 0) {
            echo "Patch applied to workspace."
            env.PATCH_APPLIED = 'true'
          } else {
            echo "Patch application failed (rc=${applyRc}). Will apply safe simulated fallback."
            env.PATCH_APPLIED = 'false'
            // fallback: append safe comment to index.html (non-destructive)
            bat 'echo <!-- SAFE FALLBACK PATCH (AUTO-HEAL) --> >> index.html'
          }
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
            git config user.email "autoheal@jenkins.local"
            git config user.name "Jenkins AutoHeal"
            git add -A
            REM commit if there are changes; exit 0 if nothing to commit
            git commit -m "Auto-healed by Jenkins + Gemini" || echo No changes to commit
            REM push using token/username
            git push https://%GIT_USER%:%GIT_PSW%@github.com/%GIT_USER%/simple-pipeline.git HEAD:${BRANCH} || echo push-failed
          """
        }
      }
    }

    stage('Trigger Vercel Deployment') {
      when {
        expression { env.BUILD_FAILED == 'true' }
      }
      steps {
        withCredentials([string(credentialsId: 'vercel-token', variable: 'VERCEL_TOKEN')]) {
          powershell '''
$ErrorActionPreference = "Stop"
# Build minimal deployment request — we must include gitSource.ref
$body = @{
  "name" = "simple-pipeline"
  "gitSource" = @{
    "type" = "github"
    "repo" = "NIKHILUTTAM/simple-pipeline"
    "org"  = "NIKHILUTTAM"
    "branch" = "main"
  }
} | ConvertTo-Json -Depth 10

$uri = "https://api.vercel.com/v13/deployments"
# call Vercel
$response = Invoke-RestMethod -Method Post -Uri $uri -Headers @{ Authorization = "Bearer $env:VERCEL_TOKEN"; "Content-Type" = "application/json" } -Body $body -ErrorAction Stop
# Save response
$response | ConvertTo-Json -Depth 10 | Out-File vercel_response.json -Encoding utf8
Write-Host "Vercel response saved to vercel_response.json"
# store status (if there is a "state" field or "error")
if ($response.error) {
  Write-Host "Vercel call returned error"
  exit 2
}
'''
        }
      }
    }

    stage('Auto-rollback if deployment failed') {
      when {
        expression { env.BUILD_FAILED == 'true' }
      }
      steps {
        script {
          // Check vercel_response.json and if contains error -> revert last commit
          def rc = powershell(returnStatus: true, script: '''
$ErrorActionPreference = "Stop"
if (-not (Test-Path vercel_response.json)) { Write-Host "no vercel_response.json"; exit 1 }
$j = Get-Content vercel_response.json -Raw | ConvertFrom-Json
if ($j.error) { Write-Host "deployment error detected"; exit 2 }
# if no explicit error, check for required URL/id
if (-not $j.id -and -not $j.url) { Write-Host "deployment response missing id/url"; exit 3 }
Write-Host "deployment looks OK"
exit 0
''')
          if (rc != 0) {
            echo "Deployment failed or response invalid (rc=${rc}) — rolling back latest commit if we pushed one."
            withCredentials([usernamePassword(credentialsId: 'github-token', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_PSW')]) {
              // Safe rollback: create a revert commit for the last autoheal commit
              bat """
                git fetch --all
                REM find last commit author "Jenkins AutoHeal"
                setlocal enabledelayedexpansion
                for /f "delims=" %%a in ('git log -n 1 --pretty=format:"%%H %%an"') do set L=%%a
                echo Last commit header: !L!
                REM Attempt revert - if nothing to revert, echo message
                git revert --no-edit HEAD || echo "Revert failed or nothing to revert"
                git push https://%GIT_USER%:%GIT_PSW%@github.com/%GIT_USER%/simple-pipeline.git HEAD:${BRANCH} || echo "Push revert failed"
              """
            }
          } else {
            echo "Deployment succeeded (or looked OK). No rollback needed."
          }
        }
      }
    }
  } // stages

  post {
    always {
      // archive artifacts for debugging
      archiveArtifacts artifacts: 'response.json, response_body.txt, autoheal_patch.diff, vercel_response.json', allowEmptyArchive: true
      script {
        if (env.BUILD_FAILED == 'true') {
          echo "❌ Pipeline FAILED (auto-heal attempted). Check archived artifacts and Git history."
          currentBuild.result = 'FAILURE'
        } else {
          echo "✅ Pipeline successful."
          currentBuild.result = 'SUCCESS'
        }
      }
    }
  }
}
