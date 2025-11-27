pipeline {
    agent any

    // Define environment variables safely
    environment {
        REPO_URL = 'https://github.com/NIKHILUTTAM/simple-pipeline.git'
        BRANCH_NAME = 'main'
        // Using credentials binding for sensitive data
    }

    stages {
        // ---------------------------------------------------------
        // STAGE 1: Checkout Code
        // ---------------------------------------------------------
        stage('Checkout') {
            steps {
                script {
                    // Clean workspace before starting
                    deleteDir() 
                }
                // Use Jenkins Credential ID 'github-token' (Username/Password type)
                withCredentials([usernamePassword(credentialsId: 'github-token', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_PASS')]) {
                    sh '''
                        git init
                        git remote add origin ${REPO_URL}
                        git fetch --depth 1 origin ${BRANCH_NAME}
                        git checkout -b ${BRANCH_NAME} origin/${BRANCH_NAME}
                    '''
                }
            }
        }

        // ---------------------------------------------------------
        // STAGE 2: Build & Test (Simulated)
        // ---------------------------------------------------------
        stage('Build & Test') {
            steps {
                script {
                    echo "🚀 Running Build and Tests..."
                    // SIMULATION: Check for syntax errors manually to simulate failure
                    // In a real app, this would be 'npm test' or 'mvn clean install'
                    def syntaxCheck = sh(script: "grep -q '</html>' index.html", returnStatus: true)
                    
                    if (syntaxCheck != 0) {
                        echo "❌ Build Failed: Syntax Error Detected (Missing </html>)"
                        env.BUILD_STATUS = 'FAILURE'
                        // We do NOT fail the stage yet, so we can run auto-heal
                    } else {
                        echo "✅ Build Succeeded"
                        env.BUILD_STATUS = 'SUCCESS'
                    }
                }
            }
        }

        // ---------------------------------------------------------
        // STAGE 3: Call Gemini AI (Only if Build Failed)
        // ---------------------------------------------------------
        stage('AI Diagnosis') {
            when {
                expression { env.BUILD_STATUS == 'FAILURE' }
            }
            steps {
                withCredentials([string(credentialsId: 'gemini-api-key', variable: 'GEMINI_KEY')]) {
                    script {
                        echo "🤖 Asking Gemini to fix the code..."
                        
                        // Read the broken file
                        def fileContent = readFile('index.html')
                        
                        // Prepare the Python script to call Gemini
                        def pythonScript = """
import os, json, urllib.request, re

api_key = os.environ['GEMINI_KEY']
code = '''${fileContent}'''

prompt = '''
You are a DevOps Auto-Healer. 
The following HTML file caused a build failure.
It is likely missing a closing tag or has a syntax error.

CODE:
''' + code + '''

TASK: Fix the code. Output ONLY the fixed code. No markdown.
'''

url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=' + api_key
headers = {'Content-Type': 'application/json'}
data = {'contents': [{'parts': [{'text': prompt}]}]}

try:
    req = urllib.request.Request(url, json.dumps(data).encode('utf-8'), headers)
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # Clean markdown
        ai_text = re.sub(r'^```\\\\w*', '', ai_text).strip()
        ai_text = re.sub(r'```$', '', ai_text).strip()
        
        # Output ONLY the code to a file
        with open('index_fixed.html', 'w') as f:
            f.write(ai_text)
            
except Exception as e:
    print(f"Error: {e}")
    exit(1)
"""
                        // Run the Python script
                        writeFile file: 'ai_fixer.py', text: pythonScript
                        sh 'python3 ai_fixer.py'
                    }
                }
            }
        }

        // ---------------------------------------------------------
        // STAGE 4: Apply & Push Fix
        // ---------------------------------------------------------
        stage('Apply & Push Fix') {
            when {
                expression { fileExists('index_fixed.html') }
            }
            steps {
                withCredentials([usernamePassword(credentialsId: 'github-token', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_PASS')]) {
                    sh '''
                        mv index_fixed.html index.html
                        
                        git config user.email "jenkins-bot@example.com"
                        git config user.name "Jenkins Bot"
                        
                        git add index.html
                        git commit -m "🚑 Auto-Heal: Gemini fixed syntax error"
                        
                        # Push using the token credential
                        git push https://${GIT_USER}:${GIT_PASS}@github.com/NIKHILUTTAM/simple-pipeline.git ${BRANCH_NAME}
                    '''
                    echo "✅ Fix pushed to GitHub. Triggering new build..."
                }
            }
        }

        // ---------------------------------------------------------
        // STAGE 5: Deploy to Vercel (Only if Build Succeeded)
        // ---------------------------------------------------------
        stage('Deploy to Vercel') {
            when {
                expression { env.BUILD_STATUS == 'SUCCESS' }
            }
            steps {
                withCredentials([string(credentialsId: 'vercel-token', variable: 'VERCEL_TOKEN')]) {
                    sh '''
                        # Install Vercel CLI if missing
                        if ! command -v vercel &> /dev/null; then
                            npm install -g vercel
                        fi
                        
                        # Deploy
                        vercel --prod --confirm --token ${VERCEL_TOKEN}
                    '''
                }
            }
        }
    }
    
    post {
        failure {
            echo "❌ Pipeline Failed. Please check logs."
        }
    }
}