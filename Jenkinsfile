pipeline {
    agent {
        label 'vbogdtlmosp11'
    }

    environment {
        // Iniciamos en v12 si BUILD_NUMBER es 1
        BASE_VERSION = 11
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Descargando código del repositorio...'
            }
        }

        stage('Build Image') {
            steps {
                script {
                    def buildNum = env.BUILD_NUMBER.toInteger()
                    env.NEW_VERSION = "v${BASE_VERSION + buildNum}"
                    echo "Construyendo imagen versión: ${env.NEW_VERSION}"
                    
                    // Build with nerdctl
                    sh "nerdctl -n k8s.io build -t datacheck-web:${env.NEW_VERSION} ."
                }
            }
        }

        stage('Patch Deployment') {
            steps {
                echo "Actualizando deployment.yaml con la imagen: datacheck-web:${env.NEW_VERSION}"
                script {
                    // Update the image tag in deployment.yaml
                    if (isUnix()) {
                        sh "sed -i 's|image: datacheck-web:v.*|image: datacheck-web:${env.NEW_VERSION}|g' k8s/deployment.yaml"
                    } else {
                        powershell "(Get-Content k8s/deployment.yaml) -replace 'image: datacheck-web:v\\d+', 'image: datacheck-web:${env.NEW_VERSION}' | Set-Content k8s/deployment.yaml"
                    }
                }
            }
        }

        stage('Deploy (Simulation)') {
            steps {
                echo 'Desplegando la aplicación...'
                echo 'La imagen en k8s/deployment.yaml ha sido actualizada.'
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

