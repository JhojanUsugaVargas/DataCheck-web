pipeline {
    agent any

    environment {
        // Se asume que 'python' está en el PATH del servidor Jenkins
        PYTHON = "python"
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Descargando código del repositorio...'
                // Aquí Jenkins normalmente descarga de Git automáticamente
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Instalando dependencias necesarias...'
                bat "${PYTHON} -m pip install -r requirements.txt"
            }
        }

        stage('Run Unit Tests') {
            steps {
                echo 'Ejecutando pruebas de calidad (PyTest)...'
                bat "${PYTHON} -m pytest test_app.py"
            }
        }

        stage('Deploy (Simulation)') {
            steps {
                echo 'Desplegando la aplicación...'
                echo 'Para despliegue real en Windows, se suele usar un servicio de Windows o PM2.'
                // bat "python run_prod.py" // Esto bloquearía el pipeline, se suele correr en background
            }
        }
    }

    post {
        always {
            echo 'Limpiando archivos temporales...'
        }
        success {
            echo '✅ El despliegue fue exitoso!'
        }
        failure {
            echo '❌ Hubo un error en el pipeline. Revisa los logs.'
        }
    }
}
