pipeline {
    agent any

    environment {
        GITHUB_TOKEN = credentials('github-token')
        GEMINI_KEY   = credentials('gemini-key')
        VERCEL_TOKEN = credentials('vercel-token')
        REPO_URL     = "https://github.com/NIKHILUTTAM/simple-pipeline.git"
    }

    stages {

        stage('Checkout Code') {
            steps {
                git url: "${REPO_URL}", branch: "main", credentialsId: "github-token"
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                echo "Installing dependencies..."
                npm install || true
                '''  // allow fail for detection
            }
        }

        stage('Run Build') {
            steps {
                script {
                    def status = sh(script: "npm run build", returnStatus: true)

                    if (status != 0) {
                        echo "❌ Build failed — triggering auto-healing..."
                        error("BUILD_FAILED")
                    }
                }
            }
        }

        stage('AI Auto-Healing (Gemini)') {
            when { failed() }
            steps {
                script {
                    echo "🧠 Sending logs to Gemini..."

                    def logs = sh(
                        script: "cat build.log || echo 'No logs captured'",
                        returnStdout: true
                    )

                    def payload = """
                    {
                      "model": "gemini-pro",
                      "prompt": "Fix this build error:\\n${logs}",
                      "temperature": 0.2
                    }
                    """

                    writeFile file: "ai_request.json", text: payload

                    sh """
                    curl -X POST \
                        -H "Content-Type: application/json" \
                        -H "x-goog-api-key: $GEMINI_KEY" \
                        -d @ai_request.json \
                        https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent \
                        > ai_fix.json
                    """

                    echo "AI response saved: ai_fix.json"
                }
            }
        }

        stage('Apply AI Fix') {
            when { failed() }
            steps {
                script {
                    sh """
                    jq -r '.candidates[0].content.parts[0].text' ai_fix.json > patch.txt
                    """

                    sh """
                    echo "Applying patch..."
                    git apply patch.txt || true
                    git add . || true
                    git commit -m "🤖 Auto-healed by Gemini" || true
                    git push https://${GITHUB_TOKEN}@github.com/NIKHILUTTAM/simple-pipeline.git || true
                    """
                }
            }
        }

        stage('Deploy to Vercel') {
            steps {
                sh """
                echo "🔄 Triggering Vercel deployment..."
                curl -X POST "https://api.vercel.com/v13/deployments" \
                  -H "Authorization: Bearer $VERCEL_TOKEN" \
                  -H "Content-Type: application/json" \
                  -d '{"name": "simple-pipeline"}'
                """
            }
        }
    }

    post {
        success {
            echo "✅ Auto-healing pipeline successfully completed!"
        }
        failure {
            echo "❌ Pipeline failed even after auto-healing."
        }
    }
}
