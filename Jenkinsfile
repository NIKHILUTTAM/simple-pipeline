pipeline {
    agent any

    environment {
        GIT_CREDENTIALS = credentials('github-token')
        GEMINI_KEY      = credentials('gemini-key')
        VERCEL_TOKEN    = credentials('vercel-token')
    }

    stages {

        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/NIKHILUTTAM/simple-pipeline.git',
                    credentialsId: 'github-token'
            }
        }

        stage('Build') {
            steps {
                echo "Simulating build failure..."
                sh "exit 1"    // <-- this forces a failure for testing
            }
        }

        stage('AI Auto-Heal (Gemini)') {
            when {
                expression {
                    currentBuild.currentResult == 'FAILURE'
                }
            }
            steps {
                echo "Running Gemini auto-healing engine..."

                sh '''
                    echo "Calling Gemini API..."
                    curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=$GEMINI_KEY" \
                    -H "Content-Type: application/json" \
                    -d "{
                        \\"contents\\": [{\\"parts\\": [{\\"text\\": \\"Fix errors in codebase.\\"}]}]
                    }" > response.json

                    echo "Gemini response saved."
                '''

                echo "Applying fix (simulated)…"
                sh '''
                    echo "// FIX APPLIED BY GEMINI" >> index.html
                '''
            }
        }

        stage('Commit & Push Fix') {
            when {
                expression {
                    currentBuild.currentResult == 'FAILURE'
                }
            }
            steps {
                sh '''
                    git config user.email "autoheal@jenkins.com"
                    git config user.name "Jenkins AutoHeal"

                    git add .
                    git commit -m "Auto-healed by Jenkins + Gemini" || true
                    git push https://$GIT_CREDENTIALS@github.com/NIKHILUTTAM/simple-pipeline.git HEAD:main
                '''
            }
        }

        stage('Deploy to Vercel') {
            when {
                expression {
                    currentBuild.currentResult == 'FAILURE'
                }
            }
            steps {
                sh '''
                    echo "Triggering Vercel Deployment..."
                    curl -X POST "https://api.vercel.com/v13/deployments" \
                        -H "Authorization: Bearer $VERCEL_TOKEN" \
                        -H "Content-Type: application/json" \
                        -d "{\\"name\\":\\"simple-pipeline\\", \\"gitSource\\":{\\"type\\":\\"github\\"}}"
                '''
            }
        }
    }

    post {
        failure {
            echo "❌ Pipeline failed — but auto-healing ran."
        }
        success {
            echo "✅ Pipeline successful."
        }
    }
}
