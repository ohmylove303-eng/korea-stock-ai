"""
포지션 사이징 - 켈리 공식 기반 자금 관리
"""

from dataclasses import dataclass
from typing import Optional

from .config import SignalConfig, Grade
from .models import PositionSize


class PositionSizer:
    """포지션 사이징 계산기"""
    
    def __init__(self, config: SignalConfig = None):
        self.config = config or SignalConfig.default()
    
    def calculate(
        self,
        capital: float,
        grade: str,
        entry_price: int,
        stop_price: int
    ) -> PositionSize:
        """
        포지션 사이즈 계산
        
        공식:
        - 리스크 = 진입가 - 손절가
        - R 금액 = 자본 × R 비율 (0.5%)
        - 기본 수량 = R 금액 / 리스크
        - 최종 수량 = 기본 수량 × 등급 배수
        
        Args:
            capital: 총 자본금
            grade: 등급 (S, A, B, C)
            entry_price: 진입가
            stop_price: 손절가
        
        Returns:
            PositionSize
        """
        # 리스크 계산
        risk_per_share = entry_price - stop_price
        
        if risk_per_share <= 0:
            risk_per_share = int(entry_price * self.config.stop_loss_pct)
        
        # R 금액 (자본의 0.5%)
        r_value = capital * self.config.r_ratio
        
        # 기본 수량
        base_shares = int(r_value / risk_per_share) if risk_per_share > 0 else 0
        
        # 등급별 배수
        grade_enum = Grade[grade] if grade in [g.name for g in Grade] else Grade.C
        multiplier = self.config.grade_configs[grade_enum].r_multiplier
        
        # 최종 수량
        final_shares = int(base_shares * multiplier)
        
        # 총 투자금액
        total_size = final_shares * entry_price
        
        # 리스크 금액
        risk_amount = final_shares * risk_per_share
        
        return PositionSize(
            total_size=total_size,
            share_count=final_shares,
            r_value=r_value,
            risk_amount=risk_amount
        )
    
    def calculate_entry_stop_target(
        self,
        current_price: int
    ) -> tuple[int, int, int]:
        """
        진입가, 손절가, 익절가 계산
        
        Args:
            current_price: 현재가 (종가)
        
        Returns:
            (entry_price, stop_price, target_price)
        """
        entry_price = current_price
        stop_price = int(current_price * (1 - self.config.stop_loss_pct))
        target_price = int(current_price * (1 + self.config.take_profit_pct))
        
        return entry_price, stop_price, target_price
    
    def check_daily_loss_limit(
        self,
        today_losses: float,
        capital: float
    ) -> bool:
        """
        일일 손실 한도 체크
        
        Returns:
            True면 매매 중단 필요
        """
        r_value = capital * self.config.r_ratio
        limit = r_value * self.config.daily_loss_limit_r
        
        return today_losses >= limit
    
    def check_weekly_loss_limit(
        self,
        weekly_losses: float,
        capital: float
    ) -> bool:
        """
        주간 손실 한도 체크
        
        Returns:
            True면 매매 중단 필요
        """
        r_value = capital * self.config.r_ratio
        limit = r_value * self.config.weekly_loss_limit_r
        
        return weekly_losses >= limit
