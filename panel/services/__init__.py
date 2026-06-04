"""Camada de services do painel (S26-T01).

Cada service encapsula chamadas ao wrapper `api.py`, cacheando as LISTAS com
`@st.cache_data(ttl=60)` e invalidando o cache manualmente após mutações
(`<lista>.clear()`). As páginas devem consumir os services em vez de chamar
`api.list_*` diretamente.
"""
