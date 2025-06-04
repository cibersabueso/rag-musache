import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

class ClaudeClient:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no encontrada")
        
        self.client = anthropic.Anthropic(api_key=api_key)
    
    async def generate_response(self, context: str, question: str) -> str:
        """Generate response using Claude API with RAG context"""
        
        prompt = f"""Basándote únicamente en el siguiente contexto, responde la pregunta de manera precisa y completa.

Contexto:
{context}

Pregunta: {question}

Instrucciones:
- Responde únicamente basándote en la información del contexto proporcionado
- Si la respuesta no está en el contexto, indica que no tienes suficiente información
- Sé preciso y directo en tu respuesta
- Mantén un tono profesional

Respuesta:"""

        try:
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            raise Exception(f"Error al generar respuesta con Claude: {str(e)}")