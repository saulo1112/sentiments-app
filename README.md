# Despliegue de Aplicación de Análisis de Sentimientos en AWS con Alta Disponibilidad

**Estudiantes:**  
- Miguel Angel Franco Restrepo (22506163)  
- Saulo Quiñones Góngora (22506635)  
- Adrian Felipe Vargas Rojas (22505561)

**Curso:** Computación en la nube

**Institución:** Universidad Autónoma de Occidente

**Periodo:** 2026-1S

## 1. Resumen del proyecto

Este proyecto consiste en el despliegue de una aplicación de análisis de sentimientos utilizando una arquitectura en la nube con alta disponibilidad en AWS.

La solución integra componentes de Machine Learning, contenedores Docker y servicios de AWS, con el objetivo de simular un entorno de producción que garantice:

* Escalabilidad
* Tolerancia a fallos
* Separación de capas
* Seguridad en red

La aplicación permite analizar texto ingresado por el usuario y clasificarlo según su polaridad emocional, almacenando los resultados en una base de datos.

---

## 2. Objetivo de la práctica

El objetivo principal de la actividad es implementar una arquitectura distribuida que cumpla con principios de ingeniería de software y computación en la nube, específicamente:

* Despliegue de aplicaciones mediante contenedores (Docker).
* Uso de subredes privadas para servicios críticos.
* Implementación de un balanceador de carga (LB).
* Configuración de comunicación segura entre instancias.
* Validación de alta disponibilidad mediante pruebas de failover.

---

## 3. Descripción de la aplicación

La aplicación desarrollada es un sistema web de análisis de sentimientos que:

* Recibe texto ingresado por el usuario.
* Procesa el contenido mediante un modelo NLP (Natural Language Processing).
* Retorna una clasificación de sentimiento.
* Almacena los resultados en una base de datos PostgreSQL.

### Funcionalidades principales:

* Clasificación de texto en tiempo real.
* Persistencia de resultados.
* Interfaz accesible vía navegador.
* Despliegue distribuido en múltiples instancias.

---

## 4. Modelo de Machine Learning

La aplicación utiliza un modelo de Procesamiento de Lenguaje Natural (NLP) basado en:

* Hugging Face Transformers
* Modelos preentrenados de análisis de sentimientos

### Características:

* No requiere entrenamiento adicional.
* Inferencia rápida.
* Aplicable a textos en lenguaje natural.
* Integración directa con Flask.

---

## 5. Arquitectura del sistema

La solución fue desplegada en AWS utilizando una arquitectura distribuida en dos zonas de disponibilidad, siguiendo un enfoque de alta disponibilidad, aislamiento de red y control de acceso por capas.

La arquitectura combina componentes de red (VPC, subredes, Internet Gateway, NAT Gateway), cómputo (EC2), balanceo de carga (ALB) y contenedores (Docker), permitiendo simular un entorno cercano a producción.

---

### 5.1 Diseño de infraestructura

Se implementó una VPC personalizada con segmentación de red en subredes públicas y privadas, definiendo un rango CIDR que permite el direccionamiento interno entre servicios.

* **Subred pública**

  * Aloja los Bastion Hosts y el Application Load Balancer.
  * Asociada a un Internet Gateway para acceso externo.
  * Contiene el NAT Gateway que permite salida a internet desde subredes privadas.

* **Subred privada A (AZ A)**

  * Contiene la instancia IA-server-A.
  * No expuesta directamente a internet.

* **Subred privada B (AZ B)**

  * Contiene la instancia IA-server-B.
  * Aislada de acceso público.

Este diseño garantiza que los servicios críticos (aplicación y base de datos) operen únicamente dentro de la red privada, mientras que el acceso externo se controla exclusivamente a través del Load Balancer.

---

### 5.1.1 Conectividad a internet (IGW + NAT Gateway)

Para habilitar la comunicación con internet de forma segura, se configuraron dos componentes clave:

#### Internet Gateway (IGW)

* Asociado a la VPC.
* Permite tráfico entrante y saliente en la subred pública.
* Configurado en la tabla de rutas:

```
0.0.0.0/0 → Internet Gateway (Ruta por defecto hacia internet)
```

#### NAT Gateway (NGW)

* Desplegado en la subred pública
* Asociado a la tabla de rutas de las subredes privadas:

```
0.0.0.0/0 → NAT Gateway (Ruta por defecto para tráfico saliente desde subredes privadas hacia internet)
```

#### Importancia del NAT Gateway

El NAT Gateway es un componente crítico en esta arquitectura, ya que:

* Permite a las instancias privadas acceder a internet (ej: instalar Docker, hacer `docker pull`).
* Evita que estas instancias tengan IP pública.
* Mantiene el aislamiento de seguridad.

Sin este componente, las instancias privadas no podrían descargar dependencias ni comunicarse con servicios externos.

---

### 5.2 Instancias EC2

Se utilizaron diferentes tipos de instancia según el rol:

* **IA-server-A (t3.medium – subred privada A)**

  * Contenedor de aplicación (Flask).
  * Contenedor de base de datos PostgreSQL.
  * Nodo principal de persistencia de datos.

* **IA-server-B (t3.medium – subred privada B)**

  * Contenedor de aplicación únicamente.
  * Conexión a PostgreSQL en IA-server-A mediante IP privada.

* **Bastion Host (t3.micro – subred pública)**

  * Punto de entrada seguro para administración.
  * Permite acceso SSH a instancias privadas sin exponerlas a internet.

---

### 5.3 Contenerización

Cada instancia ejecuta servicios mediante Docker:

* IA-server-A:

  * Servicio `app` (Flask)
  * Servicio `db` (PostgreSQL)

* IA-server-B:

  * Servicio `app`

La comunicación entre servicios se realiza a través de la red privada de la VPC.

Adicionalmente, las instancias privadas dependen del NAT Gateway para descargar imágenes desde Docker Hub y paquetes del sistema.

---

### 5.4 Application Load Balancer (ALB)

Se configuró un Application Load Balancer de tipo internet-facing con las siguientes características:

* **Listener HTTP (puerto 80)**

  * Recibe tráfico desde internet.
  * Redirige solicitudes al Target Group.

* **Target Group**

  * Instancias registradas:

    * IA-server-A
    * IA-server-B
  * Puerto de destino: **5000**
  * Protocolo: HTTP

* **Health Checks**

  * Ruta: `/`
  * Intervalo configurable.
  * Detección automática de instancias no disponibles.

#### Comportamiento del ALB

* Distribución de tráfico tipo round-robin.
* Eliminación automática de instancias unhealthy.
* Redirección del tráfico hacia nodos disponibles en caso de falla.
* Durante transiciones de estado (healthy/unhealthy) pueden presentarse errores temporales (HTTP 502), asociados al tiempo de detección del health check.

---

### 5.5 Configuración de Security Groups

Se implementó un modelo de seguridad basado en principio de mínimo privilegio, alineado con la arquitectura de red (IGW + NAT Gateway), garantizando que solo los componentes necesarios tengan acceso a internet.

#### Bastion Host Security Group

* Entrada:

  * SSH (22) desde la IP del usuario.
* Salida:

  * Acceso a instancias privadas.

---

#### IA Servers Security Group (`ia-services-sg`)

* Entrada:

  * SSH (22) desde Bastion Host.

  * HTTP interno (5000) desde:

    * Security Group del ALB.
    * Bastion (para pruebas).

  * PostgreSQL (5432) desde:

    * el mismo security group (`ia-services-sg`).

    Esto permite comunicación entre IA-server-A y IA-server-B dentro de la VPC.

* Salida:

  * Acceso hacia red interna y salida a internet a través del NAT Gateway.

---

#### LB Security Group

* Entrada:

  * HTTP (80) desde internet (`0.0.0.0/0`)
* Salida:

  * Tráfico hacia instancias en puerto 5000

---

### 5.6 Flujo de tráfico

El flujo de la aplicación se define en tres niveles:

#### Entrada (usuario → sistema)

1. El usuario accede al DNS del LB.
2. El ALB recibe la solicitud HTTP (puerto 80).
3. El tráfico se enruta a una instancia disponible (A o B) en puerto 5000.

---

#### Comunicación interna (app → base de datos)

4. Si la solicitud requiere persistencia:

   * IA-server-B se comunica con PostgreSQL en IA-server-A (puerto 5432).

---

#### Salida a internet (instancias privadas)

5. Cuando las instancias requieren acceso externo:

   * El tráfico se enruta hacia el NAT Gateway.
   * El NAT Gateway accede a internet mediante el Internet Gateway.

---

### 5.7 Consideraciones de alta disponibilidad

* Despliegue en múltiples AZ.
* Balanceo activo-activo en capa de aplicación.
* Detección de fallos mediante health checks.
* Failover automático gestionado por el ALB.
* Aislamiento de base de datos en una única instancia (posible punto único de falla).

---

### 5.8 Observaciones técnicas

* La comunicación entre instancias se realiza exclusivamente por IP privada.
* No se exponen servicios internos directamente a internet.
* El NAT Gateway permite operación segura de instancias privadas sin IP pública.
* El uso de Docker facilita portabilidad y despliegue reproducible.
* La separación de roles (app vs db) permite escalabilidad futura.

### 5.9 Diagrama de la arquitectura diseñada

En la figura planteada a continuación, se evidencia el diagrama con el diseño de la arquitectura realizada.

---

## 6. Diseño de alta disponibilidad

La arquitectura implementa un esquema activo-activo en la capa de aplicación:

* Ambas instancias (A y B) pueden atender solicitudes.
* El ALB distribuye tráfico automáticamente.
* En caso de falla de una instancia:

  * El balanceador detecta el fallo.
  * Redirige el tráfico a la instancia disponible.

Esto garantiza continuidad del servicio.

---

## 7. Estructura del proyecto

```
sentiment-app/
│
├── app/
│   ├── docker-compose.yml        # Definición de servicios (app + db en A)
│   ├── Dockerfile               # Configuración de imagen
│
├── src/                         # Código de la aplicación
│   ├── main.py                  # Punto de entrada Flask
│   ├── model.py                 # Carga del modelo NLP
│   ├── database.py              # Conexión a PostgreSQL
│   └── utils.py                 # Funciones auxiliares
│
├── requirements.txt             # Dependencias
└── README.md
```

---

Perfecto, aquí sí vale la pena ser más técnico y apoyarse en fragmentos de código. Te dejo el apartado mejorado con explicación clara y viñetas donde aporta valor:

---

## 8. Despliegue con Docker

La aplicación fue desplegada utilizando **Docker y Docker Compose**, lo que permitió definir de forma declarativa los servicios, sus dependencias y la configuración necesaria para su ejecución en cada instancia.

El despliegue se realizó de forma diferenciada en cada servidor, de acuerdo con el rol dentro de la arquitectura.

---

### 8.1 IA-server-A (Aplicación + Base de datos)

En la instancia IA-server-A se ejecutan dos servicios: la aplicación y la base de datos. El siguiente fragmento muestra la configuración principal:

```yaml
services:
  db:
    image: postgres:15
    container_name: sentiment-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: sentimentdb
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password123
    ports:
      - "5432:5432"

  app:
    image: adrianfvr999/sentiment-app:latest
    container_name: sentiment-app
    restart: unless-stopped
    environment:
      DB_HOST: db
      DB_PORT: 5432
      DB_NAME: sentimentdb
      DB_USER: admin
      DB_PASSWORD: password123
    ports:
      - "5000:5000"
    depends_on:
      - db
```

**Explicación:**

* El servicio `db` utiliza la imagen oficial de PostgreSQL 15 y expone el puerto **5432**, permitiendo conexiones desde otras instancias dentro de la VPC.
* Las variables de entorno inicializan automáticamente la base de datos, el usuario y la contraseña.
* El servicio `app` ejecuta la aplicación Flask y se conecta a la base de datos utilizando el hostname interno `db`, gracias a la red de Docker Compose.
* El puerto **5000** se expone para permitir el acceso desde el Load Balancer.
* La directiva `depends_on` asegura que el contenedor de la base de datos se inicie antes que la aplicación.

---

### 8.2 IA-server-B (Solo aplicación)

En la instancia IA-server-B se ejecuta únicamente el servicio de aplicación, el cual se conecta a la base de datos ubicada en IA-server-A:

```yaml
services:
  app:
    image: adrianfvr999/sentiment-app:latest
    container_name: sentiment-app
    restart: unless-stopped
    environment:
      DB_HOST: <IP_PRIVADA_IA_SERVER_A>
      DB_PORT: 5432
      DB_NAME: sentimentdb
      DB_USER: admin
      DB_PASSWORD: password123
    ports:
      - "5000:5000"
```

**Explicación:**

* En este caso no se define un servicio de base de datos, ya que se reutiliza el contenedor PostgreSQL desplegado en IA-server-A.
* La variable `DB_HOST` se configura con la IP privada de IA-server-A, permitiendo la comunicación entre instancias dentro de la VPC.
* La aplicación mantiene la misma configuración lógica, lo que garantiza consistencia en el comportamiento entre nodos.
* El puerto **5000** se expone para que el Application Load Balancer pueda enrutar tráfico hacia esta instancia.

---

### 8.3 Consideraciones de diseño

* Se evita la duplicación de la base de datos, centralizando la persistencia en IA-server-A.
* Ambas instancias ejecutan la misma imagen de aplicación, lo que permite balanceo de carga homogéneo.
* La comunicación entre contenedores en IA-server-A se realiza mediante red interna de Docker, mientras que la comunicación entre instancias se realiza mediante la red privada de AWS.
* El uso de variables de entorno permite desacoplar la configuración de la infraestructura respecto al código de la aplicación.
* La exposición de puertos se limita a los estrictamente necesarios (5000 para la app y 5432 para PostgreSQL).

---

### 8.4 Ejecución de los servicios

En ambas instancias, los servicios se levantan mediante:

```bash
docker-compose up -d
```

Este comando crea la red, inicializa los contenedores y ejecuta los servicios en segundo plano, asegurando su disponibilidad para ser consumidos por el Load Balancer.

**Nota:** El despliegue de contenedores en las instancias privadas depende directamente del correcto funcionamiento del NAT Gateway, sin este no se podrían descargar imágenes desde Docker Hub o instalar dependencias del sistema.

---

## 9. Configuración de red

La comunicación entre los componentes del sistema se realiza principalmente mediante direcciones IP privadas dentro de la VPC, garantizando aislamiento y seguridad en la capa de red.

```
IA-server-B → IA-server-A (PostgreSQL)
```

Este esquema permite que la aplicación en múltiples instancias acceda a la base de datos sin exponer servicios críticos a internet.

---

### Arquitectura de conectividad

La red se diseñó combinando componentes clave de AWS:

* **Internet Gateway (IGW)**

  * Permite acceso a internet desde la subred pública
  * Utilizado por el Application Load Balancer y el Bastion Host

* **NAT Gateway**

  * Desplegado en la subred pública
  * Permite que las instancias en subredes privadas accedan a internet sin tener IP pública
  * Utilizado para:

    * Instalación de dependencias
    * Descarga de imágenes Docker
    * Actualizaciones del sistema

* **Subredes privadas**

  * No reciben tráfico directo desde internet
  * Solo pueden comunicarse:

    * Internamente dentro de la VPC
    * Hacia internet a través del NAT Gateway

---

### Puertos utilizados

* **80** → acceso público (Application Load Balancer)
* **5000** → aplicación (Flask)
* **5432** → PostgreSQL
* **22** → acceso administrativo (SSH vía Bastion Host)

---

### Reglas de comunicación (Security Groups)

Los Security Groups fueron configurados para permitir únicamente el tráfico necesario:

* **Tráfico interno entre instancias**

  * Comunicación entre IA-server-A y IA-server-B en puerto 5432 (PostgreSQL)
  * Permitido mediante referencia al mismo Security Group

* **Acceso del ALB a la aplicación**

  * El Load Balancer puede enrutar tráfico hacia las instancias en puerto 5000

* **Acceso administrativo**

  * SSH (puerto 22) únicamente permitido desde el Bastion Host

* **Salida a internet desde instancias privadas**

  * Permitida únicamente a través del NAT Gateway

---

### Consideraciones de diseño

* Se evita la exposición directa de las instancias privadas a internet.
* Todo el tráfico entrante pasa por el Application Load Balancer.
* Todo el tráfico saliente desde subredes privadas pasa por el NAT Gateway.
* La arquitectura implementa un modelo de seguridad por capas (defense in depth).

---

## 10. Pruebas y validación

### 10.1 Prueba de conectividad

```bash
nc -zv <private-ip-A> 5432
```

---

### 10.2 Prueba de aplicación

```bash
curl http://localhost:5000
```

---

### 10.3 Prueba de balanceo

* Acceso al DNS del ALB
* Recarga de la página
* Verificación de alternancia entre instancias

---

### 10.4 Prueba de alta disponibilidad

* Detener contenedor en una instancia
* Verificar continuidad del servicio
* Confirmar redirección automática del tráfico

---

## 11. Resultados obtenidos

* Despliegue exitoso en múltiples zonas de disponibilidad
* Balanceo de carga funcional
* Conectividad entre instancias validada
* Persistencia de datos operativa
* Tolerancia a fallos demostrada

---

## 12. Lecciones aprendidas

* Problemas de memoria pueden simular fallos de red.
* Los health checks del ALB tienen latencia de detección.
* El NAT Gateway y el Load Balancer puede generar costos elevados.
* La separación de capas mejora la mantenibilidad.

---

## 13. Uso académico

Este proyecto fue desarrollado con fines educativos en el contexto de prácticas de computación en la nube y despliegue de aplicaciones de inteligencia artificial.
