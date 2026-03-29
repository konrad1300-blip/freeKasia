"""
Moduł integracji z LLM Bielik
Ładowanie modelu i generowanie odpowiedzi
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BielikLLM:
    """Klasa do integracji z modelem LLM Bielik"""
    
    def __init__(self, model_name: str, model_path: Optional[Path] = None, 
                 temperature: float = 0.1, max_new_tokens: int = 1024,
                 top_p: float = 0.9, repetition_penalty: float = 1.1):
        """
        Inicjalizacja modelu Bielik
        
        Args:
            model_name: Nazwa modelu z HuggingFace
            model_path: Ścieżka do lokalnego modelu (opcjonalnie)
            temperature: Temperatura generacji (niższa = mniej halucynacji)
            max_new_tokens: Maksymalna liczba nowych tokenów
            top_p: Parametr top_p dla generacji
            repetition_penalty: Kara za powtórzenia
        """
        self.model_name = model_name
        self.model_path = model_path
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens
        self.top_p = top_p
        self.repetition_penalty = repetition_penalty
        
        self.tokenizer = None
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Inicjalizacja modelu Bielik na urządzeniu: {self.device}")
    
    def load_model(self) -> bool:
        """
        Ładuje model i tokenizer
        
        Returns:
            True jeśli załadowano pomyślnie
        """
        try:
            logger.info(f"Ładowanie modelu: {self.model_name}")
            
            # Konfiguracja kwantyzacji dla oszczędności pamięci
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
            
            # Ładowanie tokenizera
            logger.info("Ładowanie tokenizera...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Dodanie tokena paddingu jeśli brak
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Ładowanie modelu
            logger.info("Ładowanie modelu (może potrwać kilka minut)...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                quantization_config=quantization_config,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.float16
            )
            
            logger.info("Model załadowany pomyślnie")
            return True
            
        except Exception as e:
            logger.error(f"Błąd ładowania modelu: {str(e)}")
            return False
    
    def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        """
        Generuje odpowiedź na podstawie promptu
        
        Args:
            prompt: Prompt użytkownika
            system_prompt: Prompt systemowy (opcjonalnie)
            
        Returns:
            Wygenerowana odpowiedź
        """
        if self.model is None or self.tokenizer is None:
            logger.error("Model nie jest załadowany")
            return "Błąd: Model nie jest załadowany. Uruchom load_model() najpierw."
        
        try:
            # Formatowanie promptu dla Bielik
            if system_prompt:
                full_prompt = f"<|system|>\n{system_prompt}</s>\n<|user|>\n{prompt}</s>\n<|assistant|>\n"
            else:
                full_prompt = f"<|user|>\n{prompt}</s>\n<|assistant|>\n"
            
            # Tokenizacja
            inputs = self.tokenizer(full_prompt, return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generacja
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    repetition_penalty=self.repetition_penalty,
                    do_sample=True if self.temperature > 0 else False,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Dekodowanie odpowiedzi
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Wyciągnięcie tylko odpowiedzi asystenta
            if "<|assistant|>" in response:
                response = response.split("<|assistant|>")[-1].strip()
            elif "assistant" in response.lower():
                # Alternatywny format
                parts = response.split("assistant")
                if len(parts) > 1:
                    response = parts[-1].strip()
            
            # Usuwanie ewentualnych końcowych tokenów
            response = response.replace("</s>", "").strip()
            
            logger.info(f"Wygenerowano odpowiedź o długości {len(response)} znaków")
            
            return response
            
        except Exception as e:
            logger.error(f"Błąd generacji odpowiedzi: {str(e)}")
            return f"Wystąpił błąd podczas generacji odpowiedzi: {str(e)}"
    
    def generate_with_context(self, question: str, context: str, system_prompt: str = "") -> str:
        """
        Generuje odpowiedź z kontekstem z bazy wektorowej
        
        Args:
            question: Pytanie użytkownika
            context: Kontekst z bazy wektorowej
            system_prompt: Prompt systemowy
            
        Returns:
            Wygenerowana odpowiedź
        """
        # Tworzenie promptu z kontekstem
        prompt = f"""Kontekst z bazy danych:
{context}

Pytanie użytkownika: {question}

Odpowiedz na pytanie na podstawie podanego kontekstu. Jeśli kontekst nie zawiera wystarczających informacji, powiedz "Nie wiem" lub "Nie mam wystarczających informacji"."""
        
        return self.generate_response(prompt, system_prompt)
    
    def is_loaded(self) -> bool:
        """Sprawdza czy model jest załadowany"""
        return self.model is not None and self.tokenizer is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Pobiera informacje o modelu
        
        Returns:
            Słownik z informacjami o modelu
        """
        info = {
            "model_name": self.model_name,
            "device": self.device,
            "temperature": self.temperature,
            "max_new_tokens": self.max_new_tokens,
            "top_p": self.top_p,
            "repetition_penalty": self.repetition_penalty,
            "is_loaded": self.is_loaded()
        }
        
        if self.is_loaded():
            info["model_parameters"] = sum(p.numel() for p in self.model.parameters())
            info["model_dtype"] = str(next(self.model.parameters()).dtype)
        
        return info


def create_llm(model_name: str, temperature: float = 0.1, 
               max_new_tokens: int = 1024) -> BielikLLM:
    """
    Tworzy instancję LLM Bielik
    
    Args:
        model_name: Nazwa modelu
        temperature: Temperatura generacji
        max_new_tokens: Maksymalna liczba tokenów
        
    Returns:
        Instancja BielikLLM
    """
    return BielikLLM(
        model_name=model_name,
        temperature=temperature,
        max_new_tokens=max_new_tokens
    )


if __name__ == "__main__":
    # Test LLM
    from config import BIELIK_MODEL_NAME, LLM_TEMPERATURE, LLM_MAX_NEW_TOKENS
    
    print("Test modelu Bielik...")
    print(f"Model: {BIELIK_MODEL_NAME}")
    print(f"Temperatura: {LLM_TEMPERATURE}")
    
    # Tworzenie instancji LLM
    llm = create_llm(BIELIK_MODEL_NAME, LLM_TEMPERATURE, LLM_MAX_NEW_TOKENS)
    
    # Informacje o modelu
    info = llm.get_model_info()
    print(f"\nInformacje o modelu:")
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # Test generacji (tylko jeśli model jest dostępny)
    print("\nUwaga: Test generacji wymaga załadowania modelu (około 7GB RAM)")
    print("Aby załadować model, odkomentuj poniższe linie:")
    print("# if llm.load_model():")
    print("#     response = llm.generate_response('Jaka jest długość elementu A?')")
    print("#     print(f'Odpowiedź: {response}')")
