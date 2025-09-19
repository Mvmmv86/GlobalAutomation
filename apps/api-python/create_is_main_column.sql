-- Adicionar coluna is_main na tabela exchange_accounts
ALTER TABLE exchange_accounts
ADD COLUMN is_main BOOLEAN DEFAULT FALSE;

-- Marcar Binance Marcus como conta principal
UPDATE exchange_accounts
SET is_main = TRUE
WHERE id = '104cd0c5-fce7-4760-91e7-abc5ba10ecff';

-- Verificar resultado
SELECT name, exchange, is_main
FROM exchange_accounts
WHERE exchange = 'binance'
ORDER BY is_main DESC, name;