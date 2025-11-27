// Jenkinsfile - Auto-heal using Gemini and apply real patch (Windows-compatible)
// - github-token: username/password (username + PAT as password)
// - gemini-key: secret text (Gemini API key)
// - vercel-token: secret text (Vercel token)

pipeline {
  agent any

  parameters {
    booleanParam(name: 'SIMULATE_FAILURE', defaultValue: true, description: 'If true the Build will simulate a failure (for testing).')
    booleanParam(name: 'APPLY_REAL_FIX', defaultValue: false, description: 'If true, the pipeline will attempt to apply Gemini-generated patch (git apply).')
    string(name: 'BRANCH', defaultValue: 'main', description: 'Branch to operate on')
  }

  environment {
    // repository settings
    REPO_NAME = "NIKHILUTTAM/simple-pipeline"
    REPO_URL  = "https://github.com/${env.REPO_NAME}.git"
    AUTOFIX_FILE = "index.html"   // fallback file used if Gemini doesn't provide a patch
    // temp files
    GEMINI_RESP = "response.json"
    PATCH_FILE  = "autoheal_patch.diff"
    VERCEL_RESP = "vercel_response.json"
  }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '30'))
  }

  stages {

    stage('Checkout') {
      steps {
        script {
          withCredentials([usernamePassword(credentialsId: 'github-token', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_PSW')]) {
            // Do a clean checkout using git CLI so later git commands operate smoothly
            bat """
              echo Initializing workspace...
              if exist .git ( rmdir /s /q .git )
              git init
              git remote add origin ${env.REPO_URL}
              set GIT_ASKPASS=echo
              git fetch --no-tags --progress https://%GIT_USER%:%GIT_PSW%@github.com/${env.REPO_NAME}.git +refs/heads/${params.BRANCH}:refs/remotes/origin/${params.BRANCH}
              git checkout -f origin/${params.BRANCH}
              git status --porcelain
            """
          }
        }
      }
    }

    stage('Run Tests / Build') {
      steps {
        script {
          if (params.SIMULATE_FAILURE) {
            echo "SIMULATING BUILD FAILURE for testing auto-heal (set SIMULATE_FAILURE=false to run real build)."
            // The following returns non-zero status -> marks build stage failed
            // We capture status and let pipeline continue to auto-heal flow
            def rc = bat(returnStatus: true, script: 'exit /b 1')
            if (rc != 0) {
              echo "Build simulated as failed (exit code ${rc})"
              currentBuild.result = 'FAILURE' // ensure downstream when() conditions detect failure
            }
          } else {
            // Replace below with your actual build/test commands (npm, mvn, etc.)
            def rc = bat(returnStatus: true, script: 'echo Building... & exit /b 0')
            if (rc != 0) {
              echo "Build returned code ${rc}"
              currentBuild.result = 'FAILURE'
            } else {
              echo "Build succeeded."
            }
          }
        }
      }
    }

    stage('Call Gemini to generate patch') {
      when {
        anyOf {
          expression { currentBuild.currentResult == 'FAILURE' }
          expression { params.SIMULATE_FAILURE == true }
        }
      }
      steps {
        script {
          withCredentials([string(credentialsId: 'gemini-key', variable: 'GEMINI_KEY')]) {
            // Remove previous files if exist
            bat "if exist ${env.GEMINI_RESP} del /f /q ${env.GEMINI_RESP}"
            bat "if exist ${env.PATCH_FILE} del /f /q ${env.PATCH_FILE}"

            // Build a prompt that asks for a minimal unified diff patch
            def prompt = """
              You are an expert software engineer. Analyze the repository and generate a minimal safe patch in unified diff format to fix the build/test failure.
              Output only JSON with fields:
                - \"summary\": short explanation
                - \"patch\": the unified diff text (escaped for JSON)
              Provide the patch in the \"patch\" field as a single string. Keep changes minimal and safe.
            """.trim()

            // Use PowerShell + curl to call Gemini and save response JSON
            // We use retries in case of transient network/LLM issues
            retry(3) {
              powershell(returnStdout: true, script: """
                \$body = @{
                  contents = @(
                    @{
                      parts = @(
                        @{ text = ${groovy.json.JsonOutput.toJson(prompt)} }
                      )
                    }
                  )
                } | ConvertTo-Json -Depth 10
                \$key = "${GEMINI_KEY}"
                # Call Gemini REST endpoint
                try {
                  \$resp = curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=\$key" -H "Content-Type: application/json" -d \$body
                  if (\$LASTEXITCODE -ne 0) { throw "curl failed: \$LASTEXITCODE" }
                  \$resp | Out-File -FilePath ${env.GEMINI_RESP} -Encoding utf8
                  Write-Output "OK"
                } catch {
                  Write-Error "Gemini call failed: \$_"
                  exit 1
                }
              """).trim()
            } // retry

            echo "Gemini response saved to ${env.GEMINI_RESP}"
            archiveArtifacts artifacts: "${env.GEMINI_RESP}", allowEmptyArchive: false
          } // withCredentials
        } // script
      } // steps
    } // stage

    stage('Extract & Validate Patch') {
      when {
        anyOf {
          expression { currentBuild.currentResult == 'FAILURE' }
          expression { params.SIMULATE_FAILURE == true }
        }
      }
      steps {
        script {
          // Default: no patch extracted
          def extracted = false

          // Try to extract 'patch' value from JSON using PowerShell robustly
          powershell(returnStdout: true, script: """
            if (-not (Test-Path -Path '${env.GEMINI_RESP}')) { Write-Output 'NO_RESP'; exit 0 }
            \$json = Get-Content -Raw -Path '${env.GEMINI_RESP}'
            # attempt to find a 'patch' field anywhere in the JSON (case-insensitive)
            try {
              # naive: look for "patch": "...." OR look for code block with diff
              if (\$json -match '"patch"\\s*:\\s*"(.*?)"') {
                \$m = [System.Text.RegularExpressions.Regex]::Match(\$json, '"patch"\\s*:\\s*"(.*?)"', [System.Text.RegularExpressions.RegexOptions]::Singleline)
                \$patchEsc = \$m.Groups[1].Value
                # unescape common JSON escapes
                \$patch = \$patchEsc -replace '\\\\r','\\r' -replace '\\\\n','\\n' -replace '\\\\t','`t' -replace '\\\\\\"','\"'
                Set-Content -Path '${env.PATCH_FILE}' -Value \$patch -Encoding utf8
                Write-Output 'PATCH_FROM_FIELD'
                exit 0
              } else {
                # Fallback: look for a fenced code block containing a unified diff
                if (\$json -match '```diff[\\s\\S]*?```') {
                  \$m = [System.Text.RegularExpressions.Regex]::Match(\$json, '```diff([\\s\\S]*?)```', [System.Text.RegularExpressions.RegexOptions]::Singleline)
                  \$patch = \$m.Groups[1].Value.Trim()
                  Set-Content -Path '${env.PATCH_FILE}' -Value \$patch -Encoding utf8
                  Write-Output 'PATCH_FROM_FENCE'
                  exit 0
                } elseif (\$json -match '(^---\\s.*\\+\\+\\+\\s.*)') {
                  # maybe the diff text appears plainly
                  \$m = [System.Text.RegularExpressions.Regex]::Match(\$json, '(^---[\\s\\S]*?\\n\\+\\+\\+[\\s\\S]*?)', [System.Text.RegularExpressions.RegexOptions]::Singleline)
                  if (\$m.Success) {
                    \$patch = \$m.Groups[1].Value
                    Set-Content -Path '${env.PATCH_FILE}' -Value \$patch -Encoding utf8
                    Write-Output 'PATCH_FROM_RAW'
                    exit 0
                  }
                }
                Write-Output 'NO_PATCH_FOUND'
                exit 0
              }
            } catch {
              Write-Error "Error while extracting patch: \$_"
              exit 0
            }
          """).trim()

          // If patch file exists and is non-empty, run git apply --check
          if (fileExists(env.PATCH_FILE) && readFile(env.PATCH_FILE).trim()) {
            echo "Patch file ${env.PATCH_FILE} created, validating with git apply --check..."
            def checkRc = bat(returnStatus: true, script: "git apply --check ${env.PATCH_FILE}")
            if (checkRc == 0) {
              echo "Patch passed git apply --check"
              extracted = true
            } else {
              echo "Patch failed git apply --check; will NOT apply. Check ${env.PATCH_FILE} and ${env.GEMINI_RESP}"
              archiveArtifacts artifacts: "${env.PATCH_FILE}", allowEmptyArchive: true
              extracted = false
            }
          } else {
            echo "No valid patch extracted from Gemini output. ${env.PATCH_FILE} missing or empty."
          }

          // Expose to next stage via env var
          env.PATCH_READY = extracted.toString()
        } // script
      } // steps
    } // stage

    stage('Apply Patch (real code edits)') {
      when {
        allOf {
          expression { params.APPLY_REAL_FIX == true }
          expression { env.PATCH_READY == 'true' }
        }
      }
      steps {
        script {
          echo "Applying patch ${env.PATCH_FILE}..."
          // apply the patch for real
          def applyRc = bat(returnStatus: true, script: "git apply ${env.PATCH_FILE}")
          if (applyRc != 0) {
            echo "git apply returned ${applyRc} — aborting apply stage"
            currentBuild.result = 'UNSTABLE'
          } else {
            echo "Patch applied locally. Staging changes..."
            bat """
              git add -A
              git status --porcelain
            """
          }
        }
      }
    }

    stage('Safe simulated fix (fallback)') {
      when {
        anyOf {
          expression { env.PATCH_READY != 'true' }
          expression { params.APPLY_REAL_FIX == false }
        }
      }
      steps {
        script {
          echo "Applying a conservative simulated safe fix (append marker) to ${env.AUTOFIX_FILE}"
          if (!fileExists(env.AUTOFIX_FILE)) {
            writeFile file: env.AUTOFIX_FILE, text: "<!-- autoheal placeholder created by Jenkins -->\n"
          }
          powershell(returnStdout: true, script: "Add-Content -Path '${env.AUTOFIX_FILE}' -Value '<!-- FIX APPLIED BY GEMINI AUTO-HEAL -->'")
          bat "git add ${env.AUTOFIX_FILE} || exit /b 0"
        }
      }
    }

    stage('Commit & Push Fix') {
      when {
        anyOf {
          expression { currentBuild.currentResult == 'FAILURE' }
          expression { params.SIMULATE_FAILURE == true }
        }
      }
      steps {
        script {
          withCredentials([usernamePassword(credentialsId: 'github-token', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_PSW')]) {
            // commit if there are changes
            def hasStaged = bat(returnStatus: true, script: 'git diff --staged --quiet || (exit 0)')
            // git diff --staged --quiet returns 1 if changes exist; bat(returnStatus) returns that numeric
            // We'll attempt commit & push, but be robust if no changes exist
            def commitRc = bat(returnStatus: true, script: 'git diff --staged --quiet || git commit -m "Auto-healed by Jenkins + Gemini [ci skip]"')
            if (commitRc == 0 || commitRc == 1) {
              // commitRc==0 means commit succeeded or there were no staged changes? different git versions differ; we'll just attempt push
              echo "Attempting to push changes..."
              retry(3) {
                // embed credentials in push URL (masked by Jenkins)
                bat """
                  git push https://%GIT_USER%:%GIT_PSW%@github.com/${env.REPO_NAME}.git HEAD:${params.BRANCH} || echo "Push failed or no changes to push"
                """
              }
            } else {
              echo "Commit step returned code ${commitRc}. Continuing pipeline (no push)."
            }
          } // withCredentials
        } // script
      } // steps
    } // stage

    stage('Trigger Vercel Deployment') {
      when {
        anyOf {
          expression { currentBuild.currentResult == 'FAILURE' }
          expression { params.SIMULATE_FAILURE == true }
        }
      }
      steps {
        script {
          withCredentials([string(credentialsId: 'vercel-token', variable: 'VERCEL_TOKEN')]) {
            // Build payload with repo ref (Vercel expects gitSource.ref)
            def payload = [
              name: env.REPO_NAME.split('/')[1],
              gitSource: [
                type: "github",
                repo: env.REPO_NAME,
                ref: params.BRANCH
              ]
            ]
            writeFile file: 'vercel_payload.json', text: groovy.json.JsonOutput.toJson(payload)
            archiveArtifacts artifacts: 'vercel_payload.json', allowEmptyArchive: true

            // Call Vercel
            def status = powershell(returnStatus: true, script: """
              \$headers = @{ Authorization = "Bearer ${VERCEL_TOKEN}"; 'Content-Type' = 'application/json' }
              \$body = Get-Content -Raw -Path 'vercel_payload.json'
              try {
                \$resp = Invoke-RestMethod -Uri 'https://api.vercel.com/v13/deployments' -Method Post -Headers \$headers -Body \$body -ErrorAction Stop
                \$resp | ConvertTo-Json -Depth 6 | Out-File -FilePath ${env.VERCEL_RESP} -Encoding utf8
                Write-Output 'VERCEL_OK'
                exit 0
              } catch {
                Write-Output 'VERCEL_ERROR'
                if (\$_ -and \$_.Exception) { Write-Output \$_.Exception.Message }
                exit 1
              }
            """)
            archiveArtifacts artifacts: env.VERCEL_RESP, allowEmptyArchive: true

            def vercelText = fileExists(env.VERCEL_RESP) ? readFile(env.VERCEL_RESP) : ''
            if (!vercelText) {
              echo "Vercel response missing or empty; treat as failure."
              env.VERCEL_FAILED = 'true'
            } else if (vercelText.toLowerCase().contains('"error"')) {
              echo "Vercel response contains error: ${vercelText.take(400)}"
              env.VERCEL_FAILED = 'true'
            } else {
              echo "Vercel deployment request succeeded (response archived)."
              env.VERCEL_FAILED = 'false'
            }
          } // withCredentials vercel
        } // script
      } // steps
    } // stage

    stage('Auto-rollback if deployment failed') {
      when {
        expression { env.VERCEL_FAILED == 'true' }
      }
      steps {
        script {
          echo "Deployment failed — attempting automatic rollback (revert the auto-heal commit)."
          withCredentials([usernamePassword(credentialsId: 'github-token', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_PSW')]) {
            // find last auto-heal commit by message and revert it if present
            def rc = powershell(returnStatus: true, script: """
              \$found = git log --pretty=format:'%H|%s' -n 20 | Select-String -Pattern 'Auto-healed by Jenkins' -SimpleMatch
              if (-not \$found) { Write-Output 'NO_AUTOHEAL'; exit 0 }
              \$hash = (\$found -split '\\|')[0]
              Write-Output "REVERTING:\$hash"
              git revert --no-edit \$hash
              git push https://%GIT_USER%:%GIT_PSW%@github.com/${env.REPO_NAME}.git HEAD:${params.BRANCH}
            """)
            if (rc == 0) {
              echo "Rollback/revert pushed."
            } else {
              echo "Rollback attempt returned code ${rc} (may have failed)."
            }
          }
          // Mark the build failed to make it explicit
          error("Vercel deployment failed and rollback attempted. See artifacts/response files for details.")
        }
      }
    }

  } // stages

  post {
    always {
      script {
        echo "Post: archive artifacts and show helpful hints."
        archiveArtifacts artifacts: "${env.GEMINI_RESP},${env.PATCH_FILE},${env.VERCEL_RESP}", allowEmptyArchive: true
        // Print quick guidance
        echo "If auto-heal applied real changes, review commit history. If patch failed to apply, inspect ${env.GEMINI_RESP} and ${env.PATCH_FILE}."
      }
    }
    success {
      echo "✅ Pipeline completed SUCCESS. Auto-heal (if applied) and deploy finished."
    }
    failure {
      echo "❌ Pipeline FAILED. Check archived artifacts: ${env.GEMINI_RESP}, ${env.PATCH_FILE}, ${env.VERCEL_RESP}."
    }
    unstable {
      echo "⚠ Pipeline UNSTABLE. Some steps had non-fatal errors — check logs."
    }
  }
}
