import os
import json
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import math
import hashlib
import requests
import time

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(page_title="📚 Análisis de Venta de Libros", page_icon="📚", layout="wide")

# ==============================
# ESTILOS
# ==============================
st.markdown("""
    <style>
        .metric-card {
            background: black;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            text-align: center;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================
# CÓDIGOS CIIU DE LIBRERÍAS
# ==============================
CIIU_CODIGOS = {
    "464993": "Venta al por mayor de material de papelería, libros, revistas, periódicos",
    "G4761": "Venta al por menor de libros, periódicos y artículos de papelería",
    "G47610": "Venta al por menor de libros, periódicos y artículos de papelería en comercios especializados",
    "G476101": "Venta al por menor de libros de todo tipo en establecimientos especializados",
    "G477401": "Venta al por menor de libros de segunda mano en establecimientos especializados"
}

# ==============================
# COORDENADAS DE PROVINCIAS
# ==============================
PROVINCIAS_COORDS = {
    "Pichincha": [-0.1807, -78.4678],
    "Guayas": [-2.1894, -79.8711],
    "Manabí": [-1.0659, -80.7378],
    "Tungurahua": [-1.2177, -78.6359],
    "Cotopaxi": [-0.8964, -78.6149],
    "Imbabura": [0.3516, -78.1197],
    "Carchi": [0.5879, -77.1997],
    "Esmeraldas": [0.9633, -78.1636],
    "Sucumbíos": [-0.1213, -76.3864],
    "Orellana": [-0.4661, -76.9827],
    "Pastaza": [-1.5236, -78.1177],
    "Morona Santiago": [-2.3076, -78.1847],
    "Zamora Chinchipe": [-4.7131, -78.9450],
    "Loja": [-3.9977, -79.2044],
    "El Oro": [-3.3642, -79.9633],
    "Santa Elena": [-2.2235, -80.3636],
    "Los Ríos": [-1.6298, -79.5839],
    "Chimborazo": [-1.6734, -78.6469]
}

# ==============================
# FUNCIONES AUXILIARES
# ==============================

def detectar_separador(uploaded_file):
    """Detecta separador más probable en los primeros bytes."""
    try:
        head = uploaded_file.getvalue()[:8192]
        s = head.decode('latin1', errors='ignore')
        candidates = ['|', ';', ',', '\t']
        counts = {sep: s.count(sep) for sep in candidates}
        sep = max(counts, key=counts.get)
        uploaded_file.seek(0)
        return sep
    except Exception:
        try:
            uploaded_file.seek(0)
        except:
            pass
        return '|'


def detectar_provincia(uploaded_file, df):
    """Detecta provincia automáticamente"""
    try:
        nombre = uploaded_file.name.lower()
        for prov in PROVINCIAS_COORDS:
            if prov.lower() in nombre:
                return prov
    except:
        pass
    for col in df.columns:
        if 'provincia' in col.lower():
            val = df[col].dropna().mode()
            if not val.empty:
                return val.iloc[0]
    return "Pichincha"


def filtrar_por_ciiu(df):
    """
    Filtra por códigos CIIU de librerías y por contribuyentes activos.
    """

    col_ciiu = None
    for c in df.columns:
        if 'ciiu' in c.lower():
            col_ciiu = c
            break

    if not col_ciiu:
        st.warning("No se encontró columna CIIU. Se mostrarán todos los registros.")
        return df.copy()

    df_temp = df.copy()

    # Limpiar valores CIIU 
    df_temp.loc[:, col_ciiu] = df_temp[col_ciiu].astype(str).str.strip()

    # Filtrar por CIIU
    mask = df_temp[col_ciiu].apply(lambda x: any(code in x for code in CIIU_CODIGOS.keys()))
    filtrado = df_temp[mask].copy()

    if filtrado.empty:
        st.warning("No se encontraron registros con los códigos CIIU de librerías. Se mostrarán todos.")
        return df_temp

    # Filtrar solo ACTIVO si la columna existe 
    if "ESTADO_CONTRIBUYENTE" in filtrado.columns:
        filtrado.loc[:, "ESTADO_CONTRIBUYENTE"] = (
            filtrado["ESTADO_CONTRIBUYENTE"].astype(str).str.upper().str.strip()
        )
        filtrado = filtrado[filtrado["ESTADO_CONTRIBUYENTE"] == "ACTIVO"].copy()
    else:
        st.warning("No se encontró la columna ESTADO_CONTRIBUYENTE. No se aplicó el filtro de activos.")

    return filtrado


def _parse_number_try(v):
    if pd.isna(v):
        return None
    s = str(v).strip()
    if s == '':
        return None
    s = s.replace(',', '.')
    try:
        return float(s)
    except:
        return None


def obtener_coordenadas(row):
    """Busca columnas de lat/lon con distintos nombres y formatos."""
    lat_names = ['lat', 'latitud', 'latitude', 'y']
    lon_names = ['lon', 'long', 'longitud', 'longitude', 'x']
    lat_col = next((c for c in row.index if any(n == c.lower() or n in c.lower() for n in lat_names)), None)
    lon_col = next((c for c in row.index if any(n == c.lower() or n in c.lower() for n in lon_names)), None)

    if lat_col and lon_col:
        lat = _parse_number_try(row[lat_col])
        lon = _parse_number_try(row[lon_col])
        # si los valores están invertidos (lat fuera de rango pero lon dentro), intentar swap
        if lat is not None and lon is not None:
            if (-90 <= lat <= 90) and (-180 <= lon <= 180):
                return [lat, lon]
            if (-90 <= lon <= 90) and (-180 <= lat <= 180):
                return [lon, lat]
    return None


def _jitter_coords(base, key, magnitude=0.0006):
    """Pequeña variación determinista para separar marcadores sin coords exactas."""
    key_s = str(key)
    h = int(hashlib.md5(key_s.encode()).hexdigest()[:8], 16)
    angle = (h % 360) * math.pi / 180.0
    r = ((h >> 8) % 100) / 100.0 * magnitude
    return [base[0] + r * math.cos(angle), base[1] + r * math.sin(angle)]


# -------------------------
# Geocoding cache + Nominatim
# -------------------------
GEOCODE_CACHE_PATH = os.path.join(os.getcwd(), "geocode_cache.json")

def _load_geocode_cache():
    try:
        if os.path.exists(GEOCODE_CACHE_PATH):
            with open(GEOCODE_CACHE_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
    except:
        pass
    return {}

def _save_geocode_cache(cache):
    try:
        with open(GEOCODE_CACHE_PATH, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, ensure_ascii=False, indent=2)
    except:
        pass

def geocode_parroquia(parr, canton=None, provincia=None, sleep_sec=1.0):
    """Geocodifica 'parr' usando Nominatim; resultado cacheado."""
    if not parr or str(parr).strip() == "":
        return None
    cache = _load_geocode_cache()
    key = "|".join([str(parr).strip().lower(), str(canton or "").strip().lower(), str(provincia or "").strip().lower()])
    if key in cache:
        v = cache[key]
        if v is None:
            return None
        return [v["lat"], v["lon"]]

    q_parts = [str(parr).strip()]
    if canton:
        q_parts.append(str(canton).strip())
    if provincia:
        q_parts.append(str(provincia).strip())
    q_parts.append("Ecuador")
    query = ", ".join([p for p in q_parts if p])

    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "libros-streamlit-app/1.0 (contacto)"}
    params = {"format": "json", "q": query, "limit": 1}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                item = data[0]
                lat = float(item.get("lat"))
                lon = float(item.get("lon"))
                cache[key] = {"lat": lat, "lon": lon}
                _save_geocode_cache(cache)
                time.sleep(sleep_sec)
                return [lat, lon]
    except Exception:
        pass

    # cache negative result
    cache[key] = None
    _save_geocode_cache(cache)
    time.sleep(sleep_sec)
    return None
# -------------------------

def crear_mapa(df_filtrado, provincia):
    """
    Genera mapa centrado en la provincia dada; añade capa de parroquias (si hay GeoData)
    y coloca marcadores REALES solo dentro de la provincia analizada.

    Cambios clave:
    - Si el CSV incluye columna de provincia, se filtra por ella primero (evita excluir por distancia).
    - Mejora validación de coordenadas (swap si están invertidas).
    - Radius fallback aumentado para provincias grandes, pero solo usado si no hay columna provincia ni shapefile.
    """
    df = df_filtrado.reset_index(drop=True)

    # intentar detectar columna de provincia en el dataset y filtrar por ella
    province_col_in_df = None
    for c in df.columns:
        if 'provincia' in c.lower():
            province_col_in_df = c
            break

    if province_col_in_df:
        # normalizar y filtrar filas que contengan la provincia solicitada
        try:
            mask = df[province_col_in_df].astype(str).str.lower().str.contains(str(provincia).lower(), na=False)
            if mask.any():
                df = df[mask].reset_index(drop=True)
                st.info(f"Se filtraron {mask.sum()} registros por columna '{province_col_in_df}' con provincia {provincia}.")
            else:
                st.info(f"No se encontraron filas en la columna '{province_col_in_df}' que coincidan con '{provincia}'. Se usará el dataset completo para intentar ubicar.")
        except Exception:
            pass

    # centro y radio para la provincia analizada
    centro = PROVINCIAS_COORDS.get(provincia, [-1.8312, -78.1834])
    prov_center_lat, prov_center_lon = float(centro[0]), float(centro[1])
    radius_km = 200.0  # fallback radius if no shapefile/province polygon available

    # helper distancia haversine (km)
    def _haversine_km(lat1, lon1, lat2, lon2):
        R = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    mapa = folium.Map(location=[prov_center_lat, prov_center_lon], zoom_start=10)

    # detectar columnas parroquia y canton (misma heurística)
    parroquia_col = None
    canton_col = None
    for c in df.columns:
        if c.lower() == 'descripcion_parroquia_est':
            parroquia_col = c
        if c.lower() == 'descripcion_canton_est':
            canton_col = c
    if not parroquia_col:
        for c in df.columns:
            if 'parroq' in c.lower() or 'parroquia' in c.lower():
                parroquia_col = c
                break
    if not canton_col:
        for c in df.columns:
            if 'canton' in c.lower():
                canton_col = c
                break

    def _norm_text(v):
        if pd.isna(v):
            return None
        s = str(v).strip()
        if s == '':
            return None
        if ';' in s:
            s = s.split(';')[-1].strip()
        return s.lower()

    coords_list = df.apply(obtener_coordenadas, axis=1).tolist()

    # intentar cargar GeoDataFrame de parroquias y FILTRAR por provincia si es posible
    gdf = None
    geo_paths = [
        os.path.join(os.getcwd(), "parroquias.geojson"),
        os.path.join(os.getcwd(), "data", "parroquias.geojson"),
        os.path.join(os.getcwd(), "parroquias.shp"),
        os.path.join(os.getcwd(), "data", "parroquias.shp"),
        os.path.join("/Users", "alexis", "Downloads", "code", "parroquias.geojson"),
    ]
    for p in geo_paths:
        try:
            if not p or not os.path.exists(p):
                continue
            try:
                import geopandas as gpd
                gdf = gpd.read_file(p)
                try:
                    gdf = gdf.to_crs(epsg=4326)
                except Exception:
                    pass
                break
            except Exception:
                gdf = None
                continue
        except Exception:
            continue

    parish_centroids = {}
    gdf_name_field = None
    province_field = None
    province_shape = None
    use_polygon_check = False

    if gdf is not None and not gdf.empty:
        # detectar campo nombre y campo provincia en el GeoDataFrame
        for candidate in ['nombre', 'NAME', 'NOMBRE', 'parroquia', 'PARROQUIA', 'DPA_NOM_PAR', 'NOMBRE_PAR']:
            if candidate in gdf.columns:
                gdf_name_field = candidate
                break
        for candidate in ['provincia', 'PROVINCIA', 'NOM_PROV', 'DPA_NOM_PROV', 'PROV']:
            if candidate in gdf.columns:
                province_field = candidate
                break

        # si hay campo provincia, filtrar gdf por la provincia solicitada (case-insensitive contains)
        if province_field:
            try:
                mask = gdf[province_field].astype(str).str.contains(str(provincia), case=False, na=False)
                gdf = gdf[mask]
            except Exception:
                pass

        # si quedan features, agregar capa GeoJSON y construir shape para comprobación puntual
        try:
            if not gdf.empty:
                folium.GeoJson(
                    gdf.to_json(),
                    name="Parroquias",
                    tooltip=folium.GeoJsonTooltip(fields=[gdf_name_field] if gdf_name_field else None,
                                                  aliases=["Parroquia:"] if gdf_name_field else None,
                                                  localize=True)
                ).add_to(mapa)
                # crear shape para comprobaciones puntuales
                try:
                    province_shape = gdf.unary_union
                    use_polygon_check = True
                except Exception:
                    province_shape = None
                    use_polygon_check = False
        except Exception:
            pass

        # calcular centroides reales (solo de lo que quedó en gdf)
        try:
            centroids = gdf.geometry.centroid
            for idx, row in gdf.iterrows():
                nm = None
                if gdf_name_field and pd.notna(row.get(gdf_name_field)):
                    nm = str(row[gdf_name_field]).strip().lower()
                else:
                    for k, v in row.items():
                        if k == gdf.geometry.name:
                            continue
                        if isinstance(v, str) and v.strip():
                            nm = v.strip().lower()
                            break
                if not nm:
                    continue
                try:
                    c = centroids.iloc[idx]
                    parish_centroids[nm] = [float(c.y), float(c.x)]
                except Exception:
                    continue
        except Exception:
            pass
    else:
        st.info("No se encontró GeoData local de parroquias (o no cargable). Usaremos datos del dataset y geocoding como respaldo.")

    # centroides a partir del dataset
    parr_coords = {}
    canton_coords = {}
    def _acc(d, key, coord):
        if key not in d:
            d[key] = {'lats': [], 'lons': []}
        d[key]['lats'].append(coord[0]); d[key]['lons'].append(coord[1])

    for i, row in df.iterrows():
        coord = coords_list[i]
        if coord is None:
            continue
        if parroquia_col:
            p = _norm_text(row.get(parroquia_col))
            if p:
                _acc(parr_coords, p, coord)
        if canton_col:
            c = _norm_text(row.get(canton_col))
            if c:
                _acc(canton_coords, c, coord)

    parr_from_data = {k: [sum(v['lats'])/len(v['lats']), sum(v['lons'])/len(v['lons'])] for k, v in parr_coords.items() if v['lats']}
    canton_from_data = {k: [sum(v['lats'])/len(v['lats']), sum(v['lons'])/len(v['lons'])] for k, v in canton_coords.items() if v['lats']}

    # combinar centroides reales (parish_centroids) con los del dataset; preferir parish_centroids (reales)
    merged_parr_centroids = dict(parr_from_data)
    for k, v in parish_centroids.items():
        merged_parr_centroids.setdefault(k, v)

    # búsqueda aproximada de parroquia por nombre
    def _find_parish_match(name):
        if not name:
            return None
        key = name.lower()
        if key in merged_parr_centroids:
            return merged_parr_centroids[key]
        for k in merged_parr_centroids.keys():
            if key in k or k in key:
                return merged_parr_centroids[k]
        try:
            import difflib
            matches = difflib.get_close_matches(key, list(merged_parr_centroids.keys()), n=1, cutoff=0.7)
            if matches:
                return merged_parr_centroids[matches[0]]
        except Exception:
            pass
        return None

    # geocodificar faltantes (solo las parroquias dentro del conjunto de filas a analizar)
    to_geocode = set()
    if parroquia_col:
        for i, row in df.iterrows():
            if coords_list[i] is not None:
                continue
            p = _norm_text(row.get(parroquia_col))
            if not p:
                continue
            if _find_parish_match(p) is None:
                to_geocode.add(p)
    if to_geocode:
        st.info(f"Geocodificando {len(to_geocode)} parroquias (Nominatim, cache)...")
        geocoded = 0
        for p in sorted(to_geocode):
            try:
                g = geocode_parroquia(p, provincia=provincia, sleep_sec=0.6)
                if g:
                    merged_parr_centroids[p] = g
                    geocoded += 1
            except Exception:
                continue
        if geocoded:
            st.info(f"Se geocodificaron {geocoded} parroquias (guardadas en geocode_cache.json)")

    # colocar marcadores SOLO SI QUEDAN DENTRO DE LA PROVINCIA (según polygon o prov_center + radius)
    placed_count = 0
    missing_count = 0
    excluded_outside = 0

    # if polygon check is available, import shapely Point for containment tests
    Point = None
    if use_polygon_check:
        try:
            from shapely.geometry import Point as _Point
            Point = _Point
        except Exception:
            Point = None
            use_polygon_check = False

    for i, row in df.iterrows():
        coord = coords_list[i]
        use_loc = None

        # 1) usar coords del registro si válidas
        if isinstance(coord, (list, tuple)) and len(coord) >= 2:
            try:
                # validar y swap si necesario
                lat_c = float(coord[0]); lon_c = float(coord[1])
                if not (-90 <= lat_c <= 90 and -180 <= lon_c <= 180):
                    if -90 <= lon_c <= 90 and -180 <= lat_c <= 180:
                        lat_c, lon_c = lon_c, lat_c
                use_loc = [lat_c, lon_c]
            except:
                use_loc = None

        # 2) centroid parroquia (real o dataset)
        if use_loc is None and parroquia_col:
            pname = _norm_text(row.get(parroquia_col))
            use_loc = _find_parish_match(pname)

        # 3) canton centroid si aún None
        if use_loc is None and canton_col:
            cname = _norm_text(row.get(canton_col))
            if cname and cname in canton_from_data:
                use_loc = canton_from_data[cname]

        # 4) intentar geocoding por parroquia si aún None
        if use_loc is None and parroquia_col:
            pname = _norm_text(row.get(parroquia_col))
            if pname:
                geoc = geocode_parroquia(pname, canton=_norm_text(row.get(canton_col)) if canton_col else None, provincia=provincia, sleep_sec=0.6)
                if geoc:
                    merged_parr_centroids[pname] = geoc
                    use_loc = geoc

        if use_loc is None:
            missing_count += 1
            continue

        # verificar que la ubicación esté dentro de la provincia analizada
        inside = False
        try:
            lat_val = float(use_loc[0]); lon_val = float(use_loc[1])
            if use_polygon_check and Point is not None and province_shape is not None:
                try:
                    pt = Point(lon_val, lat_val)  # shapely Point(x=lon, y=lat)
                    if province_shape.contains(pt) or province_shape.touches(pt):
                        inside = True
                except Exception:
                    inside = False
            else:
                # fallback: distancia al centro de la provincia
                dist_km = _haversine_km(prov_center_lat, prov_center_lon, lat_val, lon_val)
                inside = dist_km <= radius_km
        except Exception:
            inside = False

        if not inside:
            excluded_outside += 1
            continue

        # jitter para evitar solapamiento
        try:
            use_loc = _jitter_coords([lat_val, lon_val], key=f"{i}-{row.get(parroquia_col, '')}", magnitude=0.0005)
        except Exception:
            use_loc = [lat_val, lon_val]

        # popup
        nombre = None
        for cand in ['RAZON_SOCIAL', 'razon_social', 'Nombre', 'NOMBRE', 'razon', 'nombre']:
            if cand in row and pd.notna(row[cand]) and str(row[cand]).strip() != '':
                nombre = str(row[cand])
                break
        if not nombre:
            nombre = 'Sin nombre'

        popup_lines = [f"<b>{nombre}</b>"]
        if parroquia_col and pd.notna(row.get(parroquia_col)):
            popup_lines.append(f"Parroquia: {row.get(parroquia_col)}")
        if canton_col and pd.notna(row.get(canton_col)):
            popup_lines.append(f"Cantón: {row.get(canton_col)}")
        for col in ['DIRECCION', 'direccion', 'Direccion']:
            if col in row and pd.notna(row[col]) and str(row[col]).strip() != '':
                popup_lines.append(f"Dirección: {row[col]}")
        popup = "<br>".join(popup_lines)

        folium.Marker(location=[use_loc[0], use_loc[1]], popup=popup, icon=folium.Icon(color="blue")).add_to(mapa)
        placed_count += 1

    try:
        folium.LayerControl().add_to(mapa)
    except Exception:
        pass

    try:
        out_path = os.path.join(os.getcwd(), "map_parroquias.html")
        mapa.save(out_path)
        st.info(f"Mapa guardado en: {out_path}")
    except Exception:
        pass

    if excluded_outside > 0:
        st.warning(f"Se excluyeron {excluded_outside} ubicaciones fuera de {provincia} (según polígono o radio {int(radius_km)} km).")
    if missing_count > 0:
        st.warning(f"⚠️ {missing_count} registros no pudieron ubicarse.")
    st.info(f"Marcadores colocados dentro de {provincia}: {placed_count} / {len(df)}")

    return mapa


# ==============================
# INTERFAZ PRINCIPAL
# ==============================
st.title("📚 Análisis de Venta de Libros por Provincia")
st.caption("Sistema para analizar distribución de librerías en Ecuador")

archivo = st.file_uploader("📤 Carga tu dataset CSV", type=["csv"])

if archivo:
    try:
        # Detectar separador y leer CSV
        sep = detectar_separador(archivo)
        archivo.seek(0)
        df = pd.read_csv(archivo, sep=sep, encoding='latin1', engine='python', on_bad_lines='skip', dtype=str)

        # Si quedó todo en una columna y hay muchos ';' en el contenido, reintentar con ';'
        if df.shape[1] == 1:
            col0 = df.columns[0]
            sample = df[col0].dropna().head(5).astype(str)
            if sample.str.contains(';').sum() >= 1:
                archivo.seek(0)
                df_try = pd.read_csv(archivo, sep=';', encoding='latin1', engine='python', on_bad_lines='skip', dtype=str)
                if df_try.shape[1] > 1:
                    df = df_try
                    sep = ';'

        st.success(f"✅ Dataset cargado con {len(df)} registros. (sep='{sep}')")
        st.dataframe(df.head())

        provincia = detectar_provincia(archivo, df)
        st.info(f"📍 Provincia detectada automáticamente: **{provincia}**")

        df_filtrado = filtrar_por_ciiu(df)

# 1. DATOS FILTRADOS (VISTA PREVIA)
        st.subheader("📦 Datos filtrados (vista previa)")
        st.dataframe(df_filtrado.head(200), width='stretch')
        st.caption(f"Mostrando los primeros {min(200, len(df_filtrado))} registros de {len(df_filtrado)} totales.")

        # MÉTRICAS
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='metric-card'><h3>Total registros</h3><h2>{len(df)}</h2></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><h3>Librerías</h3><h2>{len(df_filtrado)}</h2></div>", unsafe_allow_html=True)
        with col3:
            # Parroquia con más registros: usar DESCRIPCION_PARROQUIA_EST preferente
            parroquia_col = None
            for c in df_filtrado.columns:
                if c.lower() == 'descripcion_parroquia_est':
                    parroquia_col = c
                    break
            if not parroquia_col:
                for c in df_filtrado.columns:
                    if 'parroq' in c.lower() or 'parroquia' in c.lower():
                        parroquia_col = c
                        break

            if parroquia_col:
                parr_series = df_filtrado[parroquia_col].dropna().astype(str).str.strip()
                # Si los valores aparecen concatenados con ';', intentar extraer elemento probable
                if parr_series.str.contains(';').any():
                    # tomar el último elemento como posible parroquia (común en dumps)
                    parr_series = parr_series.apply(lambda s: s.split(';')[-1].strip() if ';' in s else s)
                if not parr_series.empty:
                    top = parr_series.mode()
                    if not top.empty:
                        top_parr = top.iloc[0]
                        count = (parr_series == top_parr).sum()
                        st.markdown(f"<div class='metric-card'><h3>Parroquia con más tiendas</h3><h2>{top_parr} ({count})</h2></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='metric-card'><h3>Parroquia con más tiendas</h3><h2>Sin datos</h2></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='metric-card'><h3>Parroquia con más tiendas</h3><h2>Sin datos</h2></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='metric-card'><h3>Parroquia con más tiendas</h3><h2>No existe columna de parroquia</h2></div>", unsafe_allow_html=True)

        # MAPA
        mapa = crear_mapa(df_filtrado, provincia)
        st.subheader(f"🗺️ Mapa de librerías en {provincia}")
        st_folium(mapa, width=1400, height=600)

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
else:
    st.info("👆 Sube un archivo CSV para comenzar el análisis.")