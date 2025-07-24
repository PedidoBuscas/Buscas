-- BACKUP DAS POLÍTICAS RLS DA TABELA deposito_patente
-- Execute estes comandos após recriar a tabela para restaurar as políticas

-- 1. Habilitar RLS na tabela
ALTER TABLE deposito_patente ENABLE ROW LEVEL SECURITY;

-- 2. Política: Inserção apenas por funcionários não-admin
CREATE POLICY "deposito_patente_insert_funcionario_nao_admin"
ON "public"."deposito_patente"
TO public
WITH CHECK (
  (EXISTS ( SELECT 1
   FROM funcionario f
  WHERE ((f.id = auth.uid()) AND (f.is_admin = false))))
);

-- 3. Política: Delete para todos os usuários (baseado em user_id)
CREATE POLICY "Enable delete for users based on user_id"
ON "public"."deposito_patente"
TO public
USING (
  true
);

-- 4. Política: Inserção apenas para usuários autenticados
CREATE POLICY "Enable insert for authenticated users only"
ON "public"."deposito_patente"
TO authenticated
WITH CHECK (
  true
);

-- 5. Política: Leitura para todos os usuários
CREATE POLICY "Enable read access for all users"
ON "public"."deposito_patente"
TO public
USING (
  true
);

-- 6. Política: Inserção apenas por funcionários
CREATE POLICY "insert_apenas_funcionario"
ON "public"."deposito_patente"
TO public
WITH CHECK (
  (EXISTS ( SELECT 1
   FROM funcionario f
  WHERE (f.id = auth.uid())))
);

-- 7. Política: Select - admin vê tudo, outros veem apenas seus dados
CREATE POLICY "select_somente_seus_dados_ou_admin_tudo"
ON "public"."deposito_patente"
TO public
USING (
  ((EXISTS ( SELECT 1
   FROM funcionario f
  WHERE ((f.id = auth.uid()) AND (f.is_admin = true)))) OR ((funcionario_id = auth.uid()) OR (consultor = auth.uid())))
);

-- 8. Verificar se as políticas foram criadas corretamente
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies 
WHERE tablename = 'deposito_patente'
ORDER BY policyname; 