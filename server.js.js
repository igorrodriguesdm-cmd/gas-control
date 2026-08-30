const express = require('express');
const path = require('path');
const cors = require('cors');
const app = express();

app.use(cors());
app.use(express.json());

// Servir os arquivos estáticos da pasta 'public' (onde estão seus HTMLs)
app.use(express.static(path.join(__dirname, 'public')));

// === SUAS ROTAS DE API EXISTENTES ===
app.post('/api/login', (req, res) => {
    const { usuario, senha } = req.body;
    // Exemplo de autenticação (substitua pela sua lógica de banco de dados)
    if (usuario === 'admin' && senha === '123') {
        return res.json({ usuario: { tipo: 'admin', nome: 'Administrador' } });
    } else if (usuario === 'deposito' && senha === '123') {
        return res.json({ usuario: { tipo: 'deposito', deposito_id: 1, nome: 'Depósito Central' } });
    }
    res.status(401).json({ erro: 'Usuário ou senha inválidos' });
});

// Rota coringa para o frontend carregar as páginas HTML corretamente
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Servidor rodando na porta ${PORT}`);
});