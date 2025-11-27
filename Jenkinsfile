pipeline {
    agent any

    environment {
        GIT_CREDENTIALS = credentials('github-token')
        GEMINI_KEY      = credentials('gemini-key')
        VERCEL_TOKEN    = credentials('vercel-token')
    }

    stages {

        /* ---------------- CHECKOUT ---------------- */
        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/NIKHILUTTAM/simple-pipeline.git',
                    credentialsId: 'github-token'
            }
        }

        /* ---------------- BUILD (SOFT FAIL) ---------------- */
        stage('Build') {
            steps {
                echo "Simulating build failure..."

                script {
                    // SOFT FAIL: does NOT stop pipeline
                    def code = bat(returnStatus: true, script: "exit 1")

                    if (code != 0) {
                        echo "Build failed with code: ${code}"
                        currentBuild.result = 'FAILURE'   // Mark failure manually
                    }
                }
            }
        }

        /* ---------------- AI AUTO HEAL ---------------- */
        stage('AI Auto-Heal (Gemini)') {
            when {
                expression { currentBuild.result == 'FAILURE' }
            }
            steps {
                echo "Running Gemini auto-healing engine..."

                bat '''
                    echo Calling Gemini API...

                    curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=%GEMINI_KEY%" ^
                        -H "Content-Type: application/json" ^
                        -d "{\\"contents\\":[{\\"parts\\":[{\\"text\\":\\"Fix errors in the HTML/JS codebase\\"}]}]}" ^
                        > response.json

                    echo Gemini response saved to response.json
                '''

                echo "Applying fix (simulated)…"

                bat '''
                    echo <!-- FIX APPLIED BY GEMINI AUTO-HEAL --> >> index.html
                '''
            }
        }

        /* ---------------- COMMIT & PUSH FIX ---------------- */
        stage('Commit & Push Fix') {
            when {
                expression { currentBuild.result == 'FAILURE' }
            }
            steps {
                bat '''
                    git config user.email "autoheal@jenkins.com"
                    git config user.name "Jenkins AutoHeal"

                    git add .
                    git commit -m "Auto-healed by Jenkins + Gemini" || exit 0

                    git push https://%GIT_CREDENTIALS%@github.com/NIKHILUTTAM/simple-pipeline.git HEAD:main
                '''
            }
        }

        /* ---------------- DEPLOY TO VERCEL ---------------- */
        stage('Deploy to Vercel') {
            when {
                expression { currentBuild.result == 'FAILURE' }
            }
            steps {
                bat '''
                    echo Triggering Vercel Deployment...

                    curl -X POST "https://api.vercel.com/v13/deployments" ^
                        -H "Authorization: Bearer %VERCEL_TOKEN%" ^
                        -H "Content-Type: application/json" ^
                        -d "{\\"name\\":\\"simple-pipeline\\",\\"gitSource\\":{\\"type\\":\\"github\\"}}"
                '''
            }
        }
    }

    /* ---------------- POST ACTIONS ---------------- */
    post {
        failure {
            echo "❌ Pipeline failed — but auto-healing attempted."
        }
        success {
            echo "✅ Pipeline successful."
        }
    }
}
