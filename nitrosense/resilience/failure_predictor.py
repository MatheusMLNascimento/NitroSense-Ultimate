"""
Failure Prediction System for NitroSense Ultimate.

FEATURE #23: Previsão de Falha
MOTIVO: Detectar problemas antes que causem crashes.
- Analisa padrões históricos (ex: fan sempre para após 2h)
- Permite manutenção preventiva antes de falha total
- Alert proativo economiza restart forçado + perda de dados
- Machine learning simples (média móvel + desvio padrão) vs. overhead
"""

from typing import Dict, List, Optional, Tuple
from collections import deque
from datetime import datetime, timedelta
import statistics
from ..core.logger import logger
from ..core.constants import THERMAL_CONFIG


class FailurePredictor:
    """
    Analyzes historical patterns to predict equipment failures.
    Uses statistical analysis on sliding windows of data.
    """
    
    def __init__(self, window_size: int = 100, alert_threshold: float = 2.5):
        """
        Initialize failure predictor.
        
        Args:
            window_size: Number of readings to maintain per metric
            alert_threshold: Standard deviation multiplier for anomaly detection
        """
        self.window_size = window_size
        self.alert_threshold = alert_threshold
        
        # Historical data storage
        self.fan_rpm_history: deque = deque(maxlen=window_size)
        self.temp_history: deque = deque(maxlen=window_size)
        self.error_count_history: deque = deque(maxlen=window_size)
        self.timestamp_history: deque = deque(maxlen=window_size)
        
        # Failure pattern registry
        self.failure_patterns: Dict[str, List[str]] = {
            "fan_stall": [],          # Times when fan RPM = 0 at high temp
            "thermal_throttle": [],   # Consecutive temp > emergency_temp
            "nbfc_timeout": [],       # Error codes 101 (NBFC_TIMEOUT)
            "ec_access_fail": [],     # Error codes 104 (EC_ACCESS_FAIL)
        }
        
        # Counters for pattern detection
        self.consecutive_errors = 0
        self.last_error_timestamp = None
        
        logger.info("FailurePredictor initialized")
    
    def add_reading(
        self, 
        fan_rpm: float, 
        cpu_temp: float, 
        error_code: Optional[int] = None
    ) -> None:
        """
        Add new sensor reading to history.
        
        Args:
            fan_rpm: Current fan speed in RPM
            cpu_temp: Current CPU temperature in °C
            error_code: Optional error code (0 = no error)
        """
        timestamp = datetime.now().isoformat()
        
        self.fan_rpm_history.append(fan_rpm)
        self.temp_history.append(cpu_temp)
        self.error_count_history.append(0 if not error_code else 1)
        self.timestamp_history.append(timestamp)
        
        # Track error patterns
        if error_code:
            self.consecutive_errors += 1
            self.last_error_timestamp = timestamp
            self._track_error_pattern(error_code, timestamp)
        else:
            self.consecutive_errors = 0
    
    def predict_failures(self) -> List[Dict[str, str]]:
        """
        Analyze historical patterns and predict failures.
        
        Returns:
            List of predicted failures with descriptions
        """
        predictions = []
        
        # Need minimum data
        if len(self.fan_rpm_history) < 10:
            return predictions
        
        # Check for fan stall pattern
        fan_stall_risk = self._detect_fan_stall_pattern()
        if fan_stall_risk:
            predictions.append({
                "type": "fan_stall",
                "severity": "critical",
                "description": fan_stall_risk["message"],
                "confidence": f"{fan_stall_risk['confidence']:.1%}",
                "recommendation": "Check NBFC status and EC module: sudo systemctl status nbfc"
            })
        
        # Check for thermal throttle pattern
        thermal_throttle_risk = self._detect_thermal_throttle_pattern()
        if thermal_throttle_risk:
            predictions.append({
                "type": "thermal_throttle",
                "severity": "warning",
                "description": thermal_throttle_risk["message"],
                "confidence": f"{thermal_throttle_risk['confidence']:.1%}",
                "recommendation": "Clean fans and heatsink, or increase thermal curve"
            })
        
        # Check for NBFC/EC issues
        nbfc_risk = self._detect_nbfc_failure_pattern()
        if nbfc_risk:
            predictions.append({
                "type": "nbfc_ec_fail",
                "severity": "critical",
                "description": nbfc_risk["message"],
                "confidence": f"{nbfc_risk['confidence']:.1%}",
                "recommendation": "Restart NBFC: sudo systemctl restart nbfc_service"
            })
        
        # Check for temperature anomalies
        temp_anomaly = self._detect_temperature_anomaly()
        if temp_anomaly:
            predictions.append({
                "type": "temp_anomaly",
                "severity": "warning",
                "description": temp_anomaly["message"],
                "confidence": f"{temp_anomaly['confidence']:.1%}",
                "recommendation": "Temperature spike detected. Check running processes."
            })
        
        return predictions
    
    def _detect_fan_stall_pattern(self) -> Optional[Dict]:
        """
        Detect pattern where fan stops (RPM=0) at high temperature.
        
        Returns:
            Dict with pattern info or None
        """
        if len(self.fan_rpm_history) < 20:
            return None
        
        # Look for: high temp + zero RPM pattern
        stall_count = 0
        high_temp_count = 0
        emergency_temp = THERMAL_CONFIG["emergency_temp"]
        
        recent_readings = list(zip(
            list(self.temp_history)[-20:],
            list(self.fan_rpm_history)[-20:]
        ))
        
        for temp, rpm in recent_readings:
            if temp > emergency_temp:
                high_temp_count += 1
                if rpm == 0:
                    stall_count += 1
        
        if stall_count > 0 and high_temp_count > 0:
            confidence = stall_count / high_temp_count
            if confidence > 0.3:  # 30% of high-temp readings had zero RPM
                return {
                    "message": f"⚠️  Fan stall detected: {stall_count} incidents in last 20 readings",
                    "confidence": confidence,
                    "severity": "critical"
                }
        
        return None
    
    def _detect_thermal_throttle_pattern(self) -> Optional[Dict]:
        """
        Detect consecutive high temperature readings.
        
        Returns:
            Dict with pattern info or None
        """
        if len(self.temp_history) < 15:
            return None
        
        emergency_temp = THERMAL_CONFIG["emergency_temp"]
        recent_temps = list(self.temp_history)[-15:]
        
        # Count consecutive temps above threshold
        max_consecutive = 0
        current_consecutive = 0
        
        for temp in recent_temps:
            if temp > emergency_temp - 10:  # ~85°C
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        if max_consecutive > 8:  # 8+ consecutive readings above threshold
            confidence = max_consecutive / len(recent_temps)
            return {
                "message": f"🔥 Thermal throttle likely: {max_consecutive} consecutive high-temp readings",
                "confidence": min(confidence, 1.0),
                "severity": "warning"
            }
        
        return None
    
    def _detect_nbfc_failure_pattern(self) -> Optional[Dict]:
        """
        Detect NBFC/EC communication failures.
        
        Returns:
            Dict with pattern info or None
        """
        if self.consecutive_errors < 5:
            return None
        
        recent_errors = list(self.error_count_history)[-20:]
        error_rate = sum(recent_errors) / len(recent_errors)
        
        if error_rate > 0.4:  # 40% error rate
            return {
                "message": f"❌ NBFC/EC issues: {int(error_rate*100)}% error rate in last 20 readings",
                "confidence": error_rate,
                "severity": "critical"
            }
        
        return None
    
    def _detect_temperature_anomaly(self) -> Optional[Dict]:
        """
        Detect unusual temperature spikes using statistical methods.
        
        Returns:
            Dict with anomaly info or None
        """
        if len(self.temp_history) < 20:
            return None
        
        recent_temps = list(self.temp_history)[-20:]
        
        try:
            mean_temp = statistics.mean(recent_temps)
            stdev_temp = statistics.stdev(recent_temps)
            
            # Detect spike: current temp > mean + (2.5 * stdev)
            current_temp = recent_temps[-1]
            threshold = mean_temp + (self.alert_threshold * stdev_temp)
            
            if current_temp > threshold:
                confidence = min((current_temp - mean_temp) / (stdev_temp or 1) / 5, 1.0)
                return {
                    "message": f"📈 Temperature spike: {current_temp:.1f}°C (avg: {mean_temp:.1f}°C)",
                    "confidence": confidence,
                    "severity": "warning"
                }
        except statistics.StatisticsError:
            pass
        
        return None
    
    def _track_error_pattern(self, error_code: int, timestamp: str) -> None:
        """
        Track error codes for pattern analysis.
        
        Args:
            error_code: Error code number
            timestamp: ISO format timestamp
        """
        pattern_map = {
            101: "nbfc_timeout",      # NBFC_TIMEOUT
            104: "ec_access_fail",    # EC_ACCESS_FAIL
        }
        
        pattern_key = pattern_map.get(error_code)
        if pattern_key and pattern_key in self.failure_patterns:
            self.failure_patterns[pattern_key].append(timestamp)
            
            # Keep only recent (last 24 hours)
            cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
            self.failure_patterns[pattern_key] = [
                ts for ts in self.failure_patterns[pattern_key]
                if ts > cutoff
            ]
    
    def get_health_score(self) -> float:
        """
        Calculate overall system health (0-100).
        
        Returns:
            Health score percentage
        """
        if not self.fan_rpm_history:
            return 100.0
        
        score = 100.0
        
        # Deduct for error rate
        if len(self.error_count_history) > 10:
            error_rate = sum(list(self.error_count_history)[-10:]) / 10
            score -= error_rate * 30  # Up to 30 points
        
        # Deduct for failure patterns
        for pattern in self.failure_patterns.values():
            if len(pattern) > 3:  # More than 3 occurrences
                score -= 10
        
        return max(0.0, min(100.0, score))
    
    def reset(self) -> None:
        """Reset all historical data."""
        self.fan_rpm_history.clear()
        self.temp_history.clear()
        self.error_count_history.clear()
        self.timestamp_history.clear()
        self.failure_patterns = {k: [] for k in self.failure_patterns}
        self.consecutive_errors = 0
        logger.info("FailurePredictor history reset")
