"""
Audio Noise Detection Utility
Detects background noise in audio chunks using signal processing techniques
"""

import numpy as np
import base64
import io
from typing import Dict, Optional, Tuple
import json

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("[Audio Detection] librosa not available. Using basic signal processing only.")


def base64_audio_to_numpy(base64_audio: str, sample_rate: int = 16000) -> Optional[np.ndarray]:
    """
    Convert base64 encoded audio to numpy array
    Expected format: base64 encoded WAV or raw PCM data
    """
    try:
        # Remove data URL prefix if present
        if ',' in base64_audio:
            base64_audio = base64_audio.split(',')[1]
        
        # Decode base64
        audio_bytes = base64.b64decode(base64_audio)
        
        # Try to parse as WAV if librosa is available
        if LIBROSA_AVAILABLE:
            try:
                audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=sample_rate, mono=True)
                return audio
            except:
                pass
        
        # Fallback: assume raw PCM 16-bit
        try:
            # Ensure we have enough bytes for int16
            if len(audio_bytes) < 2:
                print("[Audio Detection] Audio data too short")
                return None
            
            # Try to decode as int16 PCM
            audio = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # Check if we got valid data
            if len(audio) == 0:
                print("[Audio Detection] Empty audio array after decoding")
                return None
            
            # Normalize to float32 [-1, 1]
            audio = audio.astype(np.float32) / 32768.0
            
            # Clip to valid range
            audio = np.clip(audio, -1.0, 1.0)
            
            # Resample if needed (basic linear interpolation)
            if len(audio) > 0 and sample_rate != 16000:
                # Simple resampling (for production, use proper resampling)
                ratio = sample_rate / 16000
                indices = np.round(np.arange(0, len(audio), ratio)).astype(int)
                indices = indices[indices < len(audio)]
                if len(indices) > 0:
                    audio = audio[indices]
                else:
                    print("[Audio Detection] No valid indices after resampling")
                    return None
            
            return audio
        except Exception as e:
            print(f"[Audio Detection] Error in fallback audio processing: {e}")
            return None
    except Exception as e:
        print(f"[Audio Detection] Error converting base64 to numpy: {e}")
        return None


def calculate_rms_energy(audio: np.ndarray) -> float:
    """Calculate RMS (Root Mean Square) energy"""
    if len(audio) == 0:
        return 0.0
    return np.sqrt(np.mean(audio ** 2))


def calculate_zero_crossing_rate(audio: np.ndarray) -> float:
    """Calculate Zero Crossing Rate (ZCR)"""
    if len(audio) == 0:
        return 0.0
    # Count sign changes
    sign_changes = np.sum(np.diff(np.signbit(audio)))
    return sign_changes / len(audio)


def calculate_spectral_flux(audio: np.ndarray, sample_rate: int = 16000) -> float:
    """
    Calculate Spectral Flux - measures how quickly the power spectrum changes
    High flux indicates sudden changes (noise, music, multiple voices)
    """
    if len(audio) < 512:
        return 0.0
    
    try:
        if LIBROSA_AVAILABLE:
            # Optimized: Use smaller FFT size for faster processing
            stft = librosa.stft(audio, n_fft=256, hop_length=128)  # Reduced from 512/256 for speed
            magnitude = np.abs(stft)
            
            # Calculate spectral flux (optimized)
            diff = np.diff(magnitude, axis=1)
            flux = np.sum(np.maximum(diff, 0), axis=0)
            return np.mean(flux)
        else:
            # Optimized: Basic FFT-based spectral flux with smaller frames
            frame_size = 256  # Reduced from 512 for faster processing
            hop_size = 128    # Reduced from 256
            flux_values = []
            prev_magnitude = None
            
            for i in range(0, len(audio) - frame_size, hop_size):
                frame = audio[i:i + frame_size]
                fft = np.fft.fft(frame)
                magnitude = np.abs(fft)
                
                if prev_magnitude is not None:
                    diff = magnitude - prev_magnitude
                    flux = np.sum(np.maximum(diff, 0))
                    flux_values.append(flux)
                
                prev_magnitude = magnitude
            
            return np.mean(flux_values) if flux_values else 0.0
    except Exception as e:
        print(f"[Audio Detection] Error calculating spectral flux: {e}")
        return 0.0


def voice_activity_detection(audio: np.ndarray, sample_rate: int = 16000) -> Tuple[bool, float]:
    """
    Simple Voice Activity Detection (VAD)
    Returns: (is_speech, confidence)
    """
    if len(audio) == 0:
        return False, 0.0
    
    # Calculate features
    rms = calculate_rms_energy(audio)
    zcr = calculate_zero_crossing_rate(audio)
    
    # Speech typically has:
    # - Moderate RMS (not too quiet, not too loud)
    # - Moderate ZCR (not too high like noise, not too low like silence)
    
    # Thresholds (tuned for 16kHz, normalized audio)
    rms_threshold_low = 0.01  # Too quiet
    rms_threshold_high = 0.5  # Too loud (likely noise)
    zcr_threshold_low = 0.01  # Too low (silence or constant tone)
    zcr_threshold_high = 0.3  # Too high (noise)
    
    # Check if it's likely speech
    is_speech = (rms_threshold_low < rms < rms_threshold_high and 
                 zcr_threshold_low < zcr < zcr_threshold_high)
    
    # Confidence based on how well it fits speech characteristics
    rms_score = 1.0 - abs(rms - 0.05) / 0.05  # Optimal around 0.05
    zcr_score = 1.0 - abs(zcr - 0.1) / 0.1  # Optimal around 0.1
    confidence = (rms_score + zcr_score) / 2.0
    confidence = max(0.0, min(1.0, confidence))
    
    return is_speech, confidence


def detect_background_noise(audio: np.ndarray, sample_rate: int = 16000) -> Dict:
    """
    Detect background noise in audio chunk
    Returns: {
        'noise': bool,
        'confidence': float,
        'noise_type': str,
        'features': dict
    }
    """
    if audio is None or len(audio) == 0:
        return {
            'noise': False,
            'confidence': 0.0,
            'noise_type': 'silence',
            'features': {}
        }
    
    # Calculate features
    rms = calculate_rms_energy(audio)
    zcr = calculate_zero_crossing_rate(audio)
    spectral_flux = calculate_spectral_flux(audio, sample_rate)
    is_speech, speech_confidence = voice_activity_detection(audio, sample_rate)
    
    # Convert all values to native Python types (not numpy types)
    features = {
        'rms': float(rms),
        'zcr': float(zcr),
        'spectral_flux': float(spectral_flux),
        'is_speech': bool(is_speech),  # Convert numpy bool_ to Python bool
        'speech_confidence': float(speech_confidence)
    }
    
    # Noise detection logic
    noise_detected = False
    noise_confidence = 0.0
    noise_type = 'clean'
    
    # Improved noise detection with better thresholds
    
    # Rule 1: Very high RMS (loud sounds) - likely noise
    # Lowered threshold for better sensitivity
    if rms > 0.25:
        noise_detected = True
        noise_confidence = min(0.95, 0.5 + (rms - 0.25) / 0.15)
        noise_type = 'loud_sound'
    
    # Rule 2: Very high spectral flux (sudden changes) - music, TV, multiple voices
    # Lowered threshold for better detection of music/TV
    if spectral_flux > 45.0:  # Lowered from 50.0
        noise_detected = True
        noise_confidence = max(noise_confidence, min(0.95, 0.6 + (spectral_flux - 45.0) / 80.0))
        if noise_type == 'clean':
            noise_type = 'music_tv_multiple_voices'
    
    # Rule 3: High ZCR but not speech - keyboard, phone sounds, fan
    # Improved threshold for better detection
    if zcr > 0.22 and not is_speech:  # Lowered from 0.25
        noise_detected = True
        noise_confidence = max(noise_confidence, min(0.85, 0.5 + (zcr - 0.22) / 0.12))
        if noise_type == 'clean':
            noise_type = 'keyboard_phone_fan'
    
    # Rule 4: Multiple voices detection (high spectral flux + moderate RMS + not clean speech)
    # Improved thresholds
    if spectral_flux > 28.0 and 0.04 < rms < 0.28 and not is_speech:  # Lowered thresholds
        noise_detected = True
        noise_confidence = max(noise_confidence, 0.75)  # Increased from 0.7
        noise_type = 'multiple_voices'
    
    # Rule 5: Very low RMS but high activity (background chatter)
    # Improved detection
    if rms < 0.025 and zcr > 0.14:  # Adjusted thresholds
        noise_detected = True
        noise_confidence = max(noise_confidence, 0.65)  # Increased from 0.6
        noise_type = 'background_chatter'
    
    # Rule 6: Moderate RMS with high spectral flux (indicates non-speech audio)
    if 0.08 < rms < 0.25 and spectral_flux > 35.0 and not is_speech:
        noise_detected = True
        noise_confidence = max(noise_confidence, 0.7)
        if noise_type == 'clean':
            noise_type = 'music_tv_multiple_voices'
    
    # If speech is detected with high confidence, reduce noise confidence
    # But be more strict - only reduce if very clear speech
    if is_speech and speech_confidence > 0.75:  # Increased from 0.7
        noise_confidence *= 0.4  # More aggressive reduction (from 0.5)
    
    # Final decision
    if noise_confidence > 0.6:
        noise_detected = True
    elif noise_confidence < 0.4:
        noise_detected = False
    
    # Ensure all values are native Python types for JSON serialization
    return {
        'noise': bool(noise_detected),  # Convert numpy bool_ to Python bool
        'confidence': float(noise_confidence),
        'noise_type': str(noise_type),
        'features': features
    }


def process_audio_chunk(base64_audio: str, sample_rate: int = 16000) -> Dict:
    """
    Main function to process audio chunk and detect noise
    """
    try:
        # Validate input
        if not base64_audio or len(base64_audio) == 0:
            return {
                'noise': False,
                'confidence': 0.0,
                'noise_type': 'silence',
                'error': 'Empty audio chunk'
            }
        
        # Convert base64 to numpy
        audio = base64_audio_to_numpy(base64_audio, sample_rate)
        
        if audio is None or len(audio) == 0:
            return {
                'noise': False,
                'confidence': 0.0,
                'noise_type': 'silence',
                'error': 'Failed to decode audio or empty audio'
            }
        
        # Validate audio array
        if not isinstance(audio, np.ndarray):
            return {
                'noise': False,
                'confidence': 0.0,
                'noise_type': 'silence',
                'error': 'Invalid audio format'
            }
        
        # Check minimum length (at least 100ms of audio)
        min_samples = int(sample_rate * 0.1)  # 100ms
        if len(audio) < min_samples:
            return {
                'noise': False,
                'confidence': 0.0,
                'noise_type': 'silence',
                'error': f'Audio too short: {len(audio)} samples (minimum: {min_samples})'
            }
        
        # Detect noise
        result = detect_background_noise(audio, sample_rate)
        
        # Ensure result has all required fields and convert to native Python types
        if 'noise' not in result:
            result['noise'] = False
        else:
            result['noise'] = bool(result['noise'])  # Convert numpy bool_ to Python bool
        
        if 'confidence' not in result:
            result['confidence'] = 0.0
        else:
            result['confidence'] = float(result['confidence'])
        
        if 'noise_type' not in result:
            result['noise_type'] = 'clean'
        else:
            result['noise_type'] = str(result['noise_type'])
        
        # Ensure features are also JSON-serializable
        if 'features' in result and isinstance(result['features'], dict):
            features = result['features']
            if 'is_speech' in features:
                features['is_speech'] = bool(features['is_speech'])
            if 'rms' in features:
                features['rms'] = float(features['rms'])
            if 'zcr' in features:
                features['zcr'] = float(features['zcr'])
            if 'spectral_flux' in features:
                features['spectral_flux'] = float(features['spectral_flux'])
            if 'speech_confidence' in features:
                features['speech_confidence'] = float(features['speech_confidence'])
        
        return result
        
    except Exception as e:
        print(f"[Audio Detection] Error processing audio chunk: {e}")
        import traceback
        traceback.print_exc()
        return {
            'noise': False,
            'confidence': 0.0,
            'noise_type': 'error',
            'error': str(e)
        }

