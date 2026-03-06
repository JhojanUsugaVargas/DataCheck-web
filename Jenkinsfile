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
                // Ejecutar nerdctl como root en el workspace correcto
                sh """
                sudo su - <<'EOF'
                cd ${WORKSPACE}
                /usr/local/bin/nerdctl --version
                EOF
                """
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
                // Actualizar deployment.yaml con la nueva imagen
                sh """
                sudo su - <<'EOF'
                cd ${WORKSPACE}
                sed -i 's|image: datacheck-web:v.*|image: datacheck-web:${env.NEW_VERSION}|g' k8s/deployment.yaml
                EOF
                """
            }
        }

        stage('Deploy (Simulation)') {
            steps {
                // Solo una simulación de despliegue
                sh """
                sudo su - <<'EOF'
                cd ${WORKSPACE}
                echo 'La imagen en k8s/deployment.yaml ha sido actualizada.'
                EOF
                """
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