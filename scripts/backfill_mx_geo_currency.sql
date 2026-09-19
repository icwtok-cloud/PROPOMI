-- Backfill idempotente: geo/moneda México y basura AR en filas MX
-- Pegar en Render shell (psql) o ejecutar vía Python + DATABASE_URL.
-- Revisar conteos ANTES y DESPUÉS con las queries de diagnóstico.

-- 1) País canónico para fuentes MX
UPDATE properties SET country = 'México'
WHERE (source = 'mercadolibre_mx'
    OR source_url ILIKE '%mercadolibre.com.mx%'
    OR source_url ILIKE '%MLM-%'
    OR external_id ILIKE 'MLM%')
  AND (country IS NULL OR country IN ('', 'Argentina', 'Mexico', 'mexico'));

-- 2) Sacar Buenos Aires / CABA de city|zone|province en filas México
UPDATE properties SET
  city = CASE
    WHEN lower(COALESCE(city,'')) LIKE '%buenos aires%'
      OR lower(COALESCE(city,'')) LIKE '%capital federal%'
      OR lower(COALESCE(city,'')) IN ('caba','bs as','bs. as.','bsas')
    THEN CASE
      WHEN province IS NOT NULL AND province <> '' AND lower(province) NOT LIKE '%buenos%'
        THEN province
      ELSE ''
    END
    ELSE city
  END,
  zone = CASE
    WHEN lower(COALESCE(zone,'')) LIKE '%buenos aires%'
      OR lower(COALESCE(zone,'')) LIKE '%capital federal%'
      OR lower(COALESCE(zone,'')) IN ('caba','bs as')
    THEN ''
    ELSE zone
  END,
  province = CASE
    WHEN lower(COALESCE(province,'')) LIKE '%buenos aires%'
      OR lower(COALESCE(province,'')) IN ('caba','capital federal','bs as')
    THEN ''
    ELSE province
  END
WHERE country = 'México';

-- 3) Moneda default MXN si quedó ARS/vacío (USD solo si ya estaba USD)
UPDATE properties SET currency = 'MXN'
WHERE country = 'México'
  AND (currency IS NULL OR currency IN ('', 'ARS', 'AR$'));

-- Diagnóstico post-backfill (correr a mano):
-- SELECT country, currency, count(*) FROM properties GROUP BY 1,2 ORDER BY 3 DESC;
-- SELECT count(*) FROM properties WHERE country='México' AND (lower(city) LIKE '%buenos%' OR lower(zone) LIKE '%buenos%');
-- SELECT count(*) FROM properties WHERE country='México';
