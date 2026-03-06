pipeline {
    agent {
        label 'vbogdtlmosp11'
    }

    environment {
        BASE_VERSION = 11
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Descargando código del repositorio...'
                checkout scm
            }
        }

        stage('Validate Tools') {
            steps {
                sh "sudo /bin/bash -c 'cd ${WORKSPACE} && /usr/local/bin/nerdctl --version'"
            }
        }

        stage('Build Image') {
            steps {
                script {
                    def buildNum = env.BUILD_NUMBER.toInteger()
                    env.NEW_VERSION = "v${BASE_VERSION + buildNum}"

                    echo "Construyendo imagen versión: ${env.NEW_VERSION}"

                    sh """
                    sudo su - <<'EOF'
                    cd ${WORKSPACE}
                    /usr/local/bin/nerdctl -n k8s.io build -t datacheck-web:${env.NEW_VERSION} .
                    EOF
                    """
                }
            }
        }

        stage('Patch Deployment') {
            steps {
                sh "sudo /bin/bash -c 'cd ${WORKSPACE} && sed -i \"s|image: datacheck-web:v.*|image: datacheck-web:${env.NEW_VERSION}|g\" k8s/deployment.yaml'"
            }
        }

        stage('Deploy (Simulation)') {
            steps {
                sh "sudo /bin/bash -c 'echo \"La imagen en k8s/deployment.yaml ha sido actualizada.\"' "
            }
        }
    }

    post {
        always {
            echo 'Limpiando archivos temporales...'
        }
        success {
            echo "✅ El despliegue de ${env.NEW_VERSION} fue exitoso!"
        }
        failure {
            echo '❌ Hubo un error en el pipeline. Revisa los logs.'
        }
    }
}