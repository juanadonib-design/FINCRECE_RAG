# FinCrece — Asistente RAG sobre documentos PDF

## Descripción general del proyecto

**FinCrece** es un chatbot basado en la técnica de **Retrieval-Augmented Generation (RAG)** que responde preguntas del usuario utilizando exclusivamente el contenido de un conjunto de documentos PDF previamente indexados. En lugar de depender únicamente del conocimiento general del modelo de lenguaje, el sistema recupera los fragmentos de texto más relevantes de los documentos fuente y los usa como contexto para generar respuestas precisas y trazables (con cita de la fuente).

En este caso, los documentos indexados corresponden al **Manual de Políticas y Procedimientos de FinCrece**, una entidad financiera ficticia/de práctica, compuesto por 5 capítulos:

1. **Política de Privacidad y Protección de Datos Crediticios**
2. **Términos y Condiciones del Financiamiento**
3. **Manual de Evaluación Crediticia** (incluye el motor de scoring "FinCrece Score")
4. **Manual de Atención al Cliente y Preguntas Frecuentes**
5. **Política de Tasas, Tarifas y Comisiones**

El asistente permite a un cliente, oficial de crédito o cualquier usuario interno consultar en lenguaje natural el contenido de estas políticas sin tener que buscar manualmente en los documentos.

El proyecto está compuesto por:
- Un **pipeline de indexación** (`index_documents.py`) que procesa los PDFs una sola vez y guarda sus representaciones vectoriales (embeddings) en una base de datos persistente.
- Una **aplicación web de chat** (`app.py`), construida con Streamlit, que permite a los usuarios hacer preguntas en tiempo real y recibir respuestas fundamentadas en los documentos.

## Arquitectura de la solución

El sistema se divide en dos flujos independientes: **indexación** (una sola vez) y **consulta** (en cada interacción del usuario).

```
┌──────────────────────────── INDEXACIÓN (una sola vez, local) ────────────────────────────┐
│                                                                                             │
│   PDFs (data/) → Extracción de texto (pypdf) → Chunking → Embeddings (Gemini) → Supabase   │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────── CONSULTA (en cada pregunta del usuario) ─────────────────────┐
│                                                                                             │
│   Usuario escribe pregunta                                                                 │
│           │                                                                                │
│           ▼                                                                                │
│   Embedding de la pregunta (Gemini)                                                        │
│           │                                                                                │
│           ▼                                                                                │
│   Búsqueda por similitud vectorial en Supabase (pgvector) → top 5 fragmentos relevantes    │
│           │                                                                                │
│           ▼                                                                                │
│   Contexto + pregunta → Modelo generativo (Gemini) → Respuesta con fuentes citadas         │
│           │                                                                                │
│           ▼                                                                                │
│   Respuesta mostrada en la interfaz de chat (Streamlit)                                    │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

**Componentes principales:**

| Componente | Archivo | Función |
|---|---|---|
| Script de indexación | `index_documents.py` | Extrae texto de los PDFs, lo divide en fragmentos (chunks), genera sus embeddings y los guarda en Supabase. Se ejecuta una sola vez (o cada vez que se agregan/actualizan documentos). |
| Motor de consulta RAG | `rag_engine.py` | Convierte la pregunta del usuario en un embedding, busca los fragmentos más similares en Supabase y genera la respuesta final con el modelo de Gemini. |
| Interfaz de usuario | `app.py` | Aplicación Streamlit con diseño de chat (múltiples conversaciones, historial, marca FinCrece) que consume `rag_engine.py`. |
| Configuración de base de datos | `supabase_setup.sql` | Script SQL que crea la tabla de vectores, el índice de búsqueda y la función de similitud en Supabase. |

## Tecnologías y herramientas utilizadas

| Categoría | Tecnología | Uso en el proyecto |
|---|---|---|
| Lenguaje | Python 3.11+ | Lógica de indexación, consulta y backend de la aplicación |
| Interfaz web | Streamlit | Interfaz de chat, manejo de sesión y despliegue |
| Modelo de embeddings | Gemini API — `gemini-embedding-001` | Convierte texto en vectores numéricos (768 dimensiones) para búsqueda semántica |
| Modelo generativo | Gemini API — `gemini-3.5-flash` | Genera la respuesta final en lenguaje natural a partir del contexto recuperado |
| Base de datos vectorial | Supabase (PostgreSQL + extensión `pgvector`) | Almacenamiento persistente de los embeddings y búsqueda por similitud de coseno |
| Procesamiento de PDF | `pypdf` | Extracción de texto de los documentos fuente |
| SDK | `google-genai` | Cliente oficial de Python para la API de Gemini |
| SDK | `supabase-py` | Cliente oficial de Python para Supabase |
| Hosting | Streamlit Community Cloud | Despliegue público y gratuito de la aplicación web |

## Instrucciones para ejecutar el proyecto

### Requisitos previos

- Python 3.11 o superior instalado.
- Una cuenta gratuita en [Google AI Studio](https://aistudio.google.com/apikey) (para la API key de Gemini).
- Una cuenta gratuita en [Supabase](https://supabase.com).

### 1. Clonar el repositorio e instalar dependencias

```bash
git clone <URL-del-repositorio>
cd rag-bot
pip install -r requirements.txt
```

### 2. Configurar la base de datos en Supabase

1. Crea un nuevo proyecto en [supabase.com](https://supabase.com).
2. Ve a **SQL Editor → New query**, pega el contenido completo de `supabase_setup.sql` y ejecútalo (**Run**). Esto crea la tabla `documents`, el índice vectorial y la función de búsqueda `match_documents`.
3. Ve a **Project Settings → API** y copia:
   - **Project URL**
   - **service_role key** (o **secret key**, según la versión del dashboard)

### 3. Configurar las variables de entorno

Crea un archivo `.streamlit/secrets.toml` (a partir de `.streamlit/secrets.toml.example`) con:

```toml
GEMINI_API_KEY = "tu_api_key_de_gemini"
SUPABASE_URL = "https://tu-proyecto.supabase.co"
SUPABASE_KEY = "tu_service_role_o_secret_key"
```

### 4. Indexar los documentos

1. Coloca los archivos PDF a indexar dentro de la carpeta `data/`.
2. Exporta las credenciales como variables de entorno (PowerShell):

```powershell
$env:GEMINI_API_KEY="tu_api_key_de_gemini"
$env:SUPABASE_URL="https://tu-proyecto.supabase.co"
$env:SUPABASE_KEY="tu_service_role_o_secret_key"
```

3. Ejecuta el script de indexación (una sola vez; se debe repetir si se agregan o modifican documentos):

```bash
python index_documents.py
```

### 5. Ejecutar la aplicación en local

```bash
streamlit run app.py
```

La aplicación estará disponible en `http://localhost:8501`.

### 6. Desplegar en la nube (Streamlit Community Cloud)

1. Sube el proyecto a un repositorio de GitHub (sin incluir `.streamlit/secrets.toml`, que contiene credenciales).
2. Entra a [share.streamlit.io](https://share.streamlit.io), conecta el repositorio y selecciona `app.py` como archivo principal.
3. En **Settings → Secrets**, agrega las mismas 3 variables del paso 3.
4. Despliega. La aplicación quedará disponible en una URL pública tipo `https://tu-app.streamlit.app`.

### Notas y límites

- El plan gratuito de Gemini tiene un límite de 100 peticiones de embeddings por minuto; el script de indexación lo respeta automáticamente con pausas y reintentos.
- Los documentos deben tener texto seleccionable (no escaneados como imagen); de lo contrario se requeriría un paso adicional de OCR.
- El plan gratuito de Supabase permite hasta 500 MB de almacenamiento, suficiente para miles de fragmentos de texto.

## Agente Inteligente Funcional

El agente es capaz de responder preguntas basadas en el contenido de documentos PDF mediante el siguiente flujo:

1. **Lectura y procesamiento del documento fuente** (`index_documents.py` / función `extract_text_from_pdf` en `rag_engine.py`): usa la librería `pypdf` para extraer el texto de cada página del PDF, lo normaliza (elimina saltos de línea y espacios redundantes) y lo divide en fragmentos (*chunks*) de ~2000 caracteres con solapamiento de 300 caracteres, preservando el nombre del documento de origen y el número de fragmento como metadato.
2. **Indexación semántica**: cada fragmento se convierte en un vector numérico (embedding) mediante el modelo `gemini-embedding-001` y se guarda en la base de datos vectorial (Supabase/pgvector) junto con su texto original y su fuente.
3. **Recuperación (Retrieval)**: ante una pregunta del usuario, el agente genera el embedding de la pregunta y busca en la base de datos los fragmentos semánticamente más cercanos (búsqueda por similitud de coseno).
4. **Generación aumentada (Augmented Generation)**: el agente arma un prompt con los fragmentos recuperados como contexto y una instrucción de sistema que restringe al modelo a responder **únicamente** con base en ese contexto, citando la fuente. El modelo `gemini-3.5-flash` genera la respuesta final.

Código relevante:
- Lectura/procesamiento del PDF: `extract_text_from_pdf()` y `chunk_text()` en `rag_engine.py` / `index_documents.py`.
- Generación de embeddings: `embed_texts()` / `embed_query()`.
- Búsqueda y respuesta: `search_documents()` y `answer_question()` en `rag_engine.py`.

## Ejemplos de preguntas que el agente puede responder

1. ¿Qué tipos de información recopila FinCrece de sus clientes y con qué finalidad?
2. ¿Cuánto tiempo conserva FinCrece los expedientes de crédito una vez terminada la relación con el cliente?
3. ¿Cuáles son los productos de financiamiento que ofrece FinCrece y para qué sirve cada uno?
4. ¿Qué se considera un evento de incumplimiento que permite a FinCrece declarar vencido anticipadamente un financiamiento?
5. ¿Qué es el FinCrece Score y qué principios de inteligencia artificial responsable aplica?
6. ¿Qué indicador utiliza FinCrece para medir la capacidad de pago de un solicitante, y cuál es el mínimo exigido?
7. ¿Qué documentos necesita preparar una PYME para solicitar un préstamo con FinCrece?
8. Si me rechazan una solicitud, ¿puedo volver a aplicar?
9. ¿Cómo se calcula el interés moratorio cuando un cliente se atrasa en el pago de una cuota?
10. ¿Qué diferencia hay entre una reestructuración y un refinanciamiento?

## Ejemplos de respuestas generadas por el agente

Capturas de interacciones reales con la aplicación desplegada:

---

**Pregunta:** ¿Qué tipos de información recopila FinCrece de sus clientes y con qué finalidad?

**Respuesta:** FinCrece recopila información con la finalidad general de evaluar, otorgar y dar seguimiento a un financiamiento empresarial, asegurar el cumplimiento normativo y gestionar la relación comercial:
- **Información bancaria** (estados de cuenta, referencias bancarias, historial de productos financieros): para el análisis de flujo de efectivo.
- **Información comercial** (referencias de proveedores/clientes, contratos, facturación histórica): para complementar el análisis cuantitativo con contexto cualitativo del negocio.
- **Información de accionistas** (composición accionaria, beneficiarios finales, antecedentes crediticios de accionistas mayoritarios): para evaluación de riesgo y debida diligencia (prevención de lavado de activos).
- **Información de representantes legales** (identificación, contacto, datos biométricos limitados): para autenticación y firma electrónica.

📎 *Capitulo_I_ Política de Privacidad y Protección de Datos Crediticios.docx.pdf*

---

**Pregunta:** ¿Cuánto tiempo conserva FinCrece los expedientes de crédito una vez terminada la relación con el cliente?

**Respuesta:** FinCrece conserva los expedientes de crédito (incluyendo documentación de respaldo y registros de consentimiento) durante la vigencia de la relación contractual y por un período adicional posterior a su terminación, conforme a los plazos mínimos de la normativa financiera y tributaria de República Dominicana. Transcurrido ese plazo, la información se elimina de forma segura o se anonimiza para fines estadísticos internos, salvo que exista una obligación legal o un procedimiento judicial/administrativo en curso.

📎 *Capitulo_II_Terminos_y_Condiciones.docx.pdf, Capitulo_I_ Política de Privacidad y Protección de Datos Crediticios.docx.pdf*

---

**Pregunta:** ¿Cuáles son los productos de financiamiento que ofrece FinCrece y para qué sirve cada uno?

**Respuesta:** FinCrece ofrece cuatro productos para PYMES:
- **Capital de Trabajo:** necesidades operativas de corto plazo (inventario, pago a proveedores).
- **Línea de Crédito Revolvente:** fondos flexibles y reutilizables hasta un límite aprobado.
- **Préstamo para Activos Fijos:** inversión en maquinaria, equipos o infraestructura.
- **Factoraje:** liquidez inmediata adelantando el valor de facturas por cobrar, descontando una comisión.

📎 *Capitulo_II_Terminos_y_Condiciones.docx.pdf, Capitulo_IV_Atencion_al_Cliente_y_FAQ.docx.pdf*

---

**Pregunta:** ¿Qué se considera un evento de incumplimiento que permite a FinCrece declarar vencido anticipadamente un financiamiento?

**Respuesta:** Constituyen eventos de incumplimiento: falta de pago de 2+ cuotas consecutivas, falsedad comprobada en las declaraciones del cliente, desvío de fondos a fines no autorizados, deterioro grave no subsanado de garantías, apertura de un proceso de insolvencia/quiebra, y comprobación de uso de fondos en lavado de activos o financiamiento del terrorismo. La mora reiterada (3+ cuotas atrasadas en 12 meses) es un factor agravante, y los casos de fraude o actividad ilícita permiten el vencimiento anticipado inmediato, sin plazo previo de subsanación.

📎 *Capitulo_II_Terminos_y_Condiciones.docx.pdf*

---

**Pregunta:** ¿Qué es el FinCrece Score y qué principios de inteligencia artificial responsable aplica?

**Respuesta:** Es el motor que calcula un puntaje de riesgo crediticio (escala 300-850, en rangos bajo/medio/alto) combinando inteligencia artificial con revisión de analistas humanos. Aplica cuatro principios: **explicabilidad** (cada decisión puede desglosarse en los factores que más influyeron), **no discriminación** (excluye variables que generen sesgos indebidos), **supervisión humana** (ningún rechazo definitivo se toma de forma 100% automatizada) y **mejora continua** (recalibración al menos anual por el equipo de Ciencia de Datos y Riesgo).

📎 *Capitulo_III_Evaluacion_Crediticia.docx.pdf, Capitulo_IV_Atencion_al_Cliente_y_FAQ.docx.pdf, Capitulo_I_ Política de Privacidad y Protección de Datos Crediticios.docx.pdf*

---

**Pregunta:** ¿Qué indicador utiliza FinCrece para medir la capacidad de pago de un solicitante, y cuál es el mínimo exigido?

**Respuesta:** Utiliza el **indicador de cobertura del servicio de la deuda**, que compara el flujo de efectivo disponible del negocio con el monto de las cuotas del financiamiento solicitado. El mínimo exigido es que el flujo de efectivo cubra al menos **1.20 veces** la cuota proyectada, considerando también el servicio de deuda de obligaciones existentes.

📎 *Capitulo_III_Evaluacion_Crediticia.docx.pdf, Capitulo_IV_Atencion_al_Cliente_y_FAQ.docx.pdf*

---

**Pregunta:** ¿Qué documentos necesita preparar una PYME para solicitar un préstamo con FinCrece?

**Respuesta:** Documentos legales de la empresa (acta constitutiva, RNC, registro mercantil), estados financieros de los últimos dos ejercicios, declaraciones tributarias recientes y estados de cuenta bancarios de los últimos seis meses. La lista exacta depende del producto y monto solicitado; deben estar vigentes, completos y legibles (idealmente escaneados en PDF), ya que los documentos vencidos o ilegibles son la causa más común de retrasos.

📎 *Capitulo_III_Evaluacion_Crediticia.docx.pdf, Capitulo_IV_Atencion_al_Cliente_y_FAQ.docx.pdf, Capitulo_I_ Política de Privacidad y Protección de Datos Crediticios.docx.pdf*

---

**Pregunta:** Si me rechazan una solicitud, ¿puedo volver a aplicar?

**Respuesta:** Sí, un rechazo no es definitivo ni permanente. Se puede presentar una nueva solicitud una vez transcurrido el plazo mínimo indicado en la notificación de rechazo, plazo que varía según el motivo específico del rechazo y se comunica junto con dicha notificación.

📎 *Capitulo_III_Evaluacion_Crediticia.docx.pdf, Capitulo_IV_Atencion_al_Cliente_y_FAQ.docx.pdf*

---

**Pregunta:** ¿Cómo se calcula el interés moratorio cuando un cliente se atrasa en el pago de una cuota?

**Respuesta:** Se aplica exclusivamente sobre el monto de la cuota o capital vencido (no sobre el saldo total, salvo vencimiento anticipado declarado), calculado desde el primer día de atraso hasta el pago efectivo. La tasa equivale a la tasa ordinaria pactada, incrementada hasta en un 50% adicional, sin exceder los límites máximos de la normativa financiera dominicana.

📎 *Capitulo_II_Terminos_y_Condiciones.docx.pdf, Capitulo_V_Tasas_Tarifas_y_Comisiones.docx.pdf*

---

**Pregunta:** ¿Qué diferencia hay entre una reestructuración y un refinanciamiento?

**Respuesta:** La **reestructuración** responde a una dificultad de pago existente del cliente; es discrecional de FinCrece y no aplica penalidad por cancelación anticipada (el saldo se incorpora al nuevo esquema). El **refinanciamiento** está disponible para clientes con buen historial que buscan mejores condiciones (cuotas más bajas, mejor tasa) sin estar en dificultades; implica una nueva evaluación de riesgo, una nueva comisión de apertura y, cuando aplique, penalidad por cancelación anticipada del financiamiento original.

📎 *Capitulo_II_Terminos_y_Condiciones.docx.pdf, Capitulo_IV_Atencion_al_Cliente_y_FAQ.docx.pdf, Capitulo_V_Tasas_Tarifas_y_Comisiones.docx.pdf*

## ☁️ Evidencia del Deploy

- **Enlace público de la aplicación:** https://fincrecerag-7dgoyizrf7ztuxvlqtsgsy.streamlit.app/
- **Captura de pantalla:**
<img width="959" height="483" alt="image" src="https://github.com/user-attachments/assets/3454df47-aae3-4cda-8ce8-268918d60650" />
