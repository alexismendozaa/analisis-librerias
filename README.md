# 📚 Sistema de Análisis de Venta de Libros por Provincia

Sistema inteligente para analizar la distribución de librerías y puntos de venta de libros en provincias de Ecuador usando IA (Google Gemini) y mapas interactivos.

## Características

- ✅ Carga de datasets CSV por provincia
- ✅ Filtrado automático por códigos CIIU de librerías
- ✅ Visualización en mapa interactivo enfocado en la provincia
- ✅ Análisis detallado con IA (Google Gemini)
- ✅ Gráficos de distribución
- ✅ Exportación de datos filtrados
- ✅ Interfaz profesional y amigable

## Requisitos

- Python 3.8+
- pip

## Instalación

1. **Clona o descarga el proyecto**

2. **Crea un entorno virtual** (opcional pero recomendado):
   \`\`\`bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   \`\`\`

3. **Instala las dependencias**:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`


## Uso

1. **Ejecuta la aplicación**:
   \`\`\`bash
   streamlit run app.py
   \`\`\`

2. **En el navegador** (se abrirá automáticamente en `http://localhost:8501`):
   - Carga tu archivo CSV
   - Selecciona la provincia a analizar
   - Explora el mapa, gráficos y análisis

## Formato del CSV

Tu archivo CSV debe incluir las siguientes columnas:

| Columna | Tipo | Descripción |
|---------|------|-------------|
| codigo_ciiu | string | Código CIIU del negocio |
| latitud | float | Latitud geográfica |
| longitud | float | Longitud geográfica |
| nombre | string | Nombre del establecimiento |
| direccion | string | Dirección física |

## Códigos CIIU Soportados

- **464993**: Venta al por mayor de material de papelería, libros, revistas, periódicos
- **G4761**: Venta al por menor de libros, periódicos y artículos de papelería
- **G47610**: Venta al por menor de libros, periódicos y artículos de papelería en comercios especializados
- **G476101**: Venta al por menor de libros de todo tipo en establecimientos especializados
- **G477401**: Venta al por menor de libros de segunda mano en establecimientos especializados

## Estructura de Provincias

El sistema incluye coordenadas para las siguientes provincias de Ecuador:
- Pichincha, Guayas, Manabí, Tungurahua, Azogues, Cotopaxi
- Imbabura, Carchi, Esmeraldas, Sucumbíos, Orellana, Pastaza
- Morona Santiago, Zamora Chinchipe, Loja, El Oro, Santa Elena
- Los Ríos, Chimborazo

## API Keys Requeridas

### Google Gemini
Actualizar instrucciones para usar Gemini en lugar de Groq

Obtén tu API key gratuita en: https://makersuite.google.com/app/apikeys

Luego configúrala en el archivo `.env`:
\`\`\`
GEMINI_API_KEY=tu_api_key_aqui
\`\`\`

## Funcionalidades Principales

### 1. 🗺️ Mapa Interactivo
- Visualiza todos los puntos de venta en un mapa
- Mapa enfocado automáticamente en la provincia seleccionada
- Marcadores con información detallada de cada negocio

### 2. 📊 Análisis de Distribución
- Gráficos de barras mostrando la distribución por código CIIU
- Estadísticas generales del dataset

### 3. 🤖 Análisis con IA
- Usa Google Gemini en lugar de Groq
- Usa Google Gemini para analizar patrones de venta
- Identifica zonas con mayor concentración de librerías
- Proporciona insights y recomendaciones
- Sugiere estrategias de expansión

### 4. 📋 Exportación de Datos
- Descarga los datos filtrados en CSV
- Preprocesados y listos para uso posterior

## Troubleshooting

### Error: "Variable GEMINI_API_KEY no configurada"
- Verifica que tu `.env` tenga la variable correctamente configurada
- Reinicia la aplicación después de modificar `.env`

### Error: "No se encontró columna de código CIIU"
- Verifica que tu CSV tenga una columna llamada `codigo_ciiu` o `Codigo_CIIU`
- Los nombres deben coincidir exactamente (sin espacios extra)

### El mapa no muestra puntos
- Verifica que tu CSV tenga columnas con latitud y longitud
- Los valores deben ser numéricos válidos
- Asegúrate de que las coordenadas sean dentro del rango: latitud (-90 a 90), longitud (-180 a 180)

## Contacto y Soporte

Para reportar problemas o sugerencias, contacta al desarrollador.

---

**Versión**: 2.0  
**Última actualización**: 2024
