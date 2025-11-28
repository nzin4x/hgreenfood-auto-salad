const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'YOUR_API_GATEWAY_URL';

export const api = {
    checkDevice: async (deviceFingerprint) => {
        const response = await fetch(`${API_BASE_URL}/auth/check-device`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({deviceFingerprint})
        });
        return response.json();
    },

    sendVerificationCode: async (email) => {
        const response = await fetch(`${API_BASE_URL}/auth/send-code`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email})
        });
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.message || '인증 코드 발송 실패');
        }
        return response.json();
    },

    verifyCode: async (email, code, deviceFingerprint) => {
        const response = await fetch(`${API_BASE_URL}/auth/verify-code`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                email,
                code,
                deviceFingerprint
            })
        });
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.message || '인증 실패');
        }
        return response.json();
    },

    registerUser: async (userData) => {
        const response = await fetch(`${API_BASE_URL}/register`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(userData)
        });
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.message || '등록 실패');
        }
        return response.json();
    },

    async checkReservation(userId, targetDate) {
        const response = await fetch(`${API_BASE_URL}/check-reservation`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                userId,
                targetDate
            })
        });
        if (!response.ok) {
            throw new Error('예약 정보 조회 실패');
        }
        return response.json();
    },

    toggleAutoReservation: async (userId, enabled) => {
        const response = await fetch(`${API_BASE_URL}/user/toggle-auto-reservation`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                userId,
                enabled
            })
        });
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.message || '자동 예약 설정 변경 실패');
        }
        return response.json();
    },

    deleteAccount: async (userId) => {
        const response = await fetch(`${API_BASE_URL}/user/delete-account`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                userId,
                confirm: true
            })
        });
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.message || '계정 삭제 실패');
        }
        return response.json();
    },

    makeImmediateReservation: async (userId) => {
        const response = await fetch(`${API_BASE_URL}/reservation/make-immediate`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ userId })
        });
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.message || '즉시 예약 실패');
        }
        return response.json();
    },

    updateUserSettings: async (userId, menuSeq, floorNm, hgUserId, hgUserPw) => {
        const body = {
            userId,
            menuSeq,
            floorNm
        };
        if (hgUserId) body.hgUserId = hgUserId;
        if (hgUserPw) body.hgUserPw = hgUserPw;
        
        const response = await fetch(`${API_BASE_URL}/user/update-settings`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.message || '설정 업데이트 실패');
        }
        return response.json();
    },

    getUserSettings: async (userId) => {
        const response = await fetch(`${API_BASE_URL}/user/get-settings?userId=${userId}`, {
            method: 'GET',
            headers: {'Content-Type': 'application/json'}
        });
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.message || '설정 조회 실패');
        }
        return response.json();
    },

    updateExclusionDates: async (userId, exclusionDates) => {
        const response = await fetch(`${API_BASE_URL}/user/update-exclusion-dates`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                userId,
                exclusionDates
            })
        });
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.message || '제외 날짜 업데이트 실패');
        }
        return response.json();
    }
};
