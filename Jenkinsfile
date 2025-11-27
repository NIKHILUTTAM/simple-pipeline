pipeline {
    agent any

    environment {
        REPO = "NIKHILUTTAM/simple-pipeline"
        BRANCH = "main"
        SITE_URL = "https://simple-pipeline.vercel.app"

        # Choose ANY AI provider ↓
        GEMINI_KEY = credentials('GEMINI_KEY')
        OPENAI_KEY = credentials('OPENAI_KEY')
    }

    stages {

        /* ----------------------------------------------
           1) HEALTH CHECK
        -----------------------------------------------*/
        stage('Health Check') {
            steps {
                script {
                    def status = sh(
                        script: "curl -s -o /dev/null -w \"%{http_code}\" ${SITE_URL}",
                        returnStdout: true
                    ).trim()

                    if (status != "200") {
                        echo "❌ Site is down — starting AI Repair pipeline"
                        currentBuild.result = "FAILURE"
                    }
                }
            }
        }

        /* ----------------------------------------------
           2) DOWNLOAD REPO + LOGS
        -----------------------------------------------*/
        stage('Fetch Repo & Logs') {
            when { expression { currentBuild.result == "FAILURE" } }

            steps {
                script {
                    sh """
                        rm -rf repo
                        git clone https://github.com/${REPO}.git repo
                        cd repo
                        ls -la
                    """
                }
            }
        }

        /* ----------------------------------------------
           3) AI Auto-Repair (Gemini or GPT-4)
        -----------------------------------------------*/
        stage('AI Auto Repair') {
            when { expression { currentBuild.result == "FAILURE" } }

            steps {
                script {
                    echo "🤖 AI Repair Starting..."

                    // Read the broken file
                    def broken = readFile("repo/index.html")

                    // PROMPT
                    def prompt = """
                    You are an expert DevOps debugging agent.
                    The following code is causing deployment failure on Vercel.
                    FIX IT COMPLETELY.

                    Rules:
                    - Return ONLY corrected code
                    - No markdown
                    - No comments
                    - Must be valid HTML/CSS/JS
                    - Do not add explanations

                    CODE:
                    ${broken}
                    """

                    def fixed = ""

                    /* ----- Prefer GEMINI ----- */
                    if (env.GEMINI_KEY?.trim()) {
                        echo "🧠 Using Gemini for repair..."
                        fixed = sh(
                            script: """
                            curl -s -X POST \\
                              -H "Content-Type: application/json" \\
                              -d '{
                                    "contents":[{"parts":[{"text":"${prompt}"}]}]
                                  }' \\
                              "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_KEY}"
                            """,
                            returnStdout: true
                        )

                        // Extract text
                        fixed = fixed.replaceAll(".*\"text\":\"", "")
                                     .replaceAll("\"}.*", "")
                                     .replace("\\n", "\n")
                    }

                    /* ----- FALLBACK TO OPENAI ----- */
                    else if (env.OPENAI_KEY?.trim()) {
                        echo "🤖 Using OpenAI GPT-4 for repair..."
                        fixed = sh(
                            script: """
                            curl https://api.openai.com/v1/chat/completions \\
                              -H "Authorization: Bearer ${OPENAI_KEY}" \\
                              -H "Content-Type: application/json" \\
                              -d '{
                                "model": "gpt-4.1",
                                "messages": [{"role": "user", "content": "${prompt}"}]
                              }'
                            """,
                            returnStdout: true
                        )

                        fixed = fixed.replaceAll(".*\"content\":\"", "")
                                     .replaceAll("\"}.*", "")
                                     .replace("\\n", "\n")
                    }

                    // Write fixed code
                    writeFile file: "repo/index.html", text: fixed
                }
            }
        }

        /* ----------------------------------------------
           4) COMMIT & PUSH AUTO-REPAIR
        -----------------------------------------------*/
        stage('Commit Fix') {
            when { expression { currentBuild.result == "FAILURE" } }

            steps {
                script {
                    sh """
                        cd repo
                        git config user.name "AI-Heal-Bot"
                        git config user.email "heal@bot.com"
                        git add index.html
                        git commit -m "🤖 Auto-Heal: AI fixed deployment error"
                        git push
                    """
                }
            }
        }

        /* ----------------------------------------------
           5) TRIGGER GITHUB ACTIONS DEPLOY
        -----------------------------------------------*/
        stage('Trigger Deploy') {
            when { expression { currentBuild.result == "FAILURE" } }

            steps {
                script {
                    echo "🚀 Deployment will be triggered automatically by GitHub Actions"
                }
            }
        }

        /* ----------------------------------------------
           6) VERIFY FIXED SITE
        -----------------------------------------------*/
        stage('Post-Repair Health Test') {
            steps {
                script {
                    sleep 20  // small wait

                    def status = sh(
                        script: "curl -s -o /dev/null -w \"%{http_code}\" ${SITE_URL}",
                        returnStdout: true
                    ).trim()

                    if (status == "200") {
                        echo "🎉 SUCCESS — Site healed & live!"
                    } else {
                        error("Still down after repair.")
                    }
                }
            }
        }

    }
}
