#!/usr/bin/env python3
"""
Handwriting OCR using Multimodal LLMs
Supports multiple providers: OpenAI GPT-4V, Anthropic Claude, Google Gemini
"""

import base64
import requests
import json
import os
from typing import Optional, Dict, Any
from pathlib import Path
import argparse
from PIL import Image
import io
from dotenv import load_dotenv

load_dotenv()

class HandwritingOCR:
    def __init__(self, provider: str = "openai"):
        """
        Initialize the HandwritingOCR with specified provider

        Args:
            provider: "openai" or "anthropic"
        """
        self.provider = provider.lower()
        self.setup_client()

    def setup_client(self):
        """Setup API client based on provider"""
        if self.provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY")
            self.base_url = "https://api.openai.com/v1/chat/completions"
            self.model = "gpt-4o"  # Updated model name

        elif self.provider == "anthropic":
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
            self.base_url = "https://api.anthropic.com/v1/messages"
            self.model = "claude-3-sonnet-20240229"
        else:
            raise ValueError(f"Unsupported provider: {self.provider}. Use 'openai' or 'anthropic'.")

        if not self.api_key:
            raise ValueError(f"API key not found for {self.provider}. Set the appropriate environment variable.")

    def encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def preprocess_image(self, image_path: str, output_path: Optional[str] = None) -> str:
        """
        Preprocess image for better OCR results
        - Convert to grayscale
        - Enhance contrast
        - Resize if too large
        """
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Resize if image is very large (max 2000px on longest side)
                max_size = 2000
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                # Save processed image
                if output_path is None:
                    output_path = f"processed_{Path(image_path).name}"

                img.save(output_path, "JPEG", quality=95)
                return output_path

        except Exception as e:
            print(f"Error preprocessing image: {e}")
            return image_path  # Return original if preprocessing fails

    def extract_text_openai(self, image_path: str) -> Dict[str, Any]:
        """Extract text using OpenAI GPT-4V"""
        base64_image = self.encode_image(image_path)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Please extract all text from this handwritten image. 
                            Follow these guidelines:
                            1. Transcribe exactly what you see, even if some words are unclear
                            2. Use [unclear] for words you cannot decipher
                            3. Maintain line breaks and paragraph structure
                            4. If you're uncertain about a word, provide your best guess followed by (?)
                            5. After the transcription, provide a confidence score (1-10) for the overall accuracy"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
        }

        response = requests.post(self.base_url, headers=headers, json=payload)
        return response.json()

    def extract_text_anthropic(self, image_path: str) -> Dict[str, Any]:
        """Extract text using Anthropic Claude"""
        base64_image = self.encode_image(image_path)

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": self.model,
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": """Please extract all text from this handwritten image. 
                            Follow these guidelines:
                            1. Transcribe exactly what you see, even if some words are unclear
                            2. Use [unclear] for words you cannot decipher
                            3. Maintain line breaks and paragraph structure
                            4. If you're uncertain about a word, provide your best guess followed by (?)
                            5. After the transcription, provide a confidence score (1-10) for the overall accuracy"""
                        }
                    ]
                }
            ]
        }

        response = requests.post(self.base_url, headers=headers, json=payload)
        return response.json()

    def extract_text_google(self, image_path: str) -> Dict[str, Any]:
        """Extract text using Google Gemini"""
        base64_image = self.encode_image(image_path)

        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": """Please extract all text from this handwritten image. 
                            Follow these guidelines:
                            1. Transcribe exactly what you see, even if some words are unclear
                            2. Use [unclear] for words you cannot decipher
                            3. Maintain line breaks and paragraph structure
                            4. If you're uncertain about a word, provide your best guess followed by (?)
                            5. After the transcription, provide a confidence score (1-10) for the overall accuracy"""
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": base64_image
                            }
                        }
                    ]
                }
            ]
        }

        url = f"{self.base_url}?key={self.api_key}"
        response = requests.post(url, headers=headers, json=payload)
        return response.json()

    def extract_text(self, image_path: str, preprocess: bool = True) -> Dict[str, Any]:
        """
        Main method to extract text from handwriting

        Args:
            image_path: Path to the image file
            preprocess: Whether to preprocess the image

        Returns:
            Dictionary containing extracted text and metadata
        """
        # Preprocess image if requested
        if preprocess:
            processed_path = self.preprocess_image(image_path)
        else:
            processed_path = image_path

        try:
            if self.provider == "openai":
                result = self.extract_text_openai(processed_path)
                print(f"DEBUG - Raw API Response: {json.dumps(result, indent=2)}")

                if 'choices' in result and len(result['choices']) > 0:
                    text = result['choices'][0]['message']['content']
                elif 'error' in result:
                    text = f"API Error: {result['error']['message']}"
                else:
                    text = f"Unexpected response format: {result}"

            elif self.provider == "anthropic":
                result = self.extract_text_anthropic(processed_path)
                print(f"DEBUG - Raw API Response: {json.dumps(result, indent=2)}")

                if 'content' in result and len(result['content']) > 0:
                    text = result['content'][0]['text']
                elif 'error' in result:
                    text = f"API Error: {result['error']['message']}"
                else:
                    text = f"Unexpected response format: {result}"
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            # Clean up processed image if it was created
            if preprocess and processed_path != image_path:
                try:
                    os.remove(processed_path)
                except:
                    pass

            return {
                "extracted_text": text,
                "provider": self.provider,
                "model": self.model,
                "original_image": image_path,
                "raw_response": result
            }

        except Exception as e:
            return {
                "extracted_text": f"Error: {str(e)}",
                "provider": self.provider,
                "model": self.model,
                "original_image": image_path,
                "error": str(e)
            }

    def batch_extract(self, image_folder: str, output_file: str = "extracted_texts.json"):
        """
        Extract text from multiple images in a folder

        Args:
            image_folder: Path to folder containing images
            output_file: Output JSON file to save results
        """
        results = []
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}

        folder_path = Path(image_folder)
        image_files = [f for f in folder_path.iterdir()
                       if f.suffix.lower() in image_extensions]

        print(f"Found {len(image_files)} images to process...")

        for i, image_file in enumerate(image_files, 1):
            print(f"Processing {i}/{len(image_files)}: {image_file.name}")

            result = self.extract_text(str(image_file))
            result['filename'] = image_file.name
            results.append(result)

        # Save results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"Results saved to {output_file}")
        return results


def main():
    parser = argparse.ArgumentParser(description="Extract text from handwritten images using multimodal LLMs")
    parser.add_argument("image_path", help="Path to image file or folder")
    parser.add_argument("--provider", choices=["openai", "anthropic"],
                        default="openai", help="LLM provider to use")
    parser.add_argument("--batch", action="store_true",
                        help="Process all images in the specified folder")
    parser.add_argument("--no-preprocess", action="store_true",
                        help="Skip image preprocessing")
    parser.add_argument("--output", default="results.json",
                        help="Output file for batch processing")

    args = parser.parse_args()

    # Initialize OCR
    try:
        ocr = HandwritingOCR(provider=args.provider)
    except ValueError as e:
        print(f"Error: {e}")
        return

    if args.batch:
        # Batch processing
        results = ocr.batch_extract(args.image_path, args.output)
        print(f"Processed {len(results)} images")
    else:
        # Single image processing
        result = ocr.extract_text(args.image_path, preprocess=not args.no_preprocess)
        print("\n" + "=" * 50)
        print("EXTRACTED TEXT:")
        print("=" * 50)
        print(result["extracted_text"])
        print("\n" + "=" * 50)
        print(f"Provider: {result['provider']}")
        print(f"Model: {result['model']}")


if __name__ == "__main__":
    main()
