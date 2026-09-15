# grafico_comparacion.py
import matplotlib.pyplot as plt
import pandas as pd

# Datos
sentimientos = ['Muy Negativo', 'Negativo', 'Neutral', 'Positivo', 'Muy Positivo']
sin_contexto = [0, 6, 9, 3, 2]
con_contexto = [1, 9, 7, 1, 2]

# Crear gráfico
fig, ax = plt.subplots(figsize=(10, 6))
x = range(len(sentimientos))
width = 0.35

bars1 = ax.bar([i - width/2 for i in x], sin_contexto, width, label='Sin Contexto', color='#3498db')
bars2 = ax.bar([i + width/2 for i in x], con_contexto, width, label='Con Contexto', color='#2ecc71')

ax.set_xlabel('Sentimiento')
ax.set_ylabel('Número de respuestas')
ax.set_title('Comparación de Análisis de Sentimiento\nCon y Sin Contexto de la Pregunta')
ax.set_xticks(x)
ax.set_xticklabels(sentimientos)
ax.legend()

# Agregar valores en las barras
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom')

plt.tight_layout()
plt.savefig('data/resultados/comparacion_sentimiento.png', dpi=150)
plt.show()