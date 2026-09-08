-- Cache du texte OCR par page : relire un résultat ne rappelle pas Mistral.
ALTER TABLE documents ADD COLUMN ocr jsonb NOT NULL DEFAULT '{}';
