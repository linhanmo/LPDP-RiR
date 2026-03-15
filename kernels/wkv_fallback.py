import torch
import torch.nn as nn


def wkv_forward_fallback(w, u, k, v):
    B, T, C = k.shape
    w = w.reshape(1, 1, C).to(k.dtype).to(k.device)
    u = u.reshape(1, 1, C).to(k.dtype).to(k.device)
    y = torch.empty_like(k)
    gamma = torch.exp(-w)
    state = torch.zeros((B, C), dtype=k.dtype, device=k.device)
    denom = torch.zeros((B, C), dtype=k.dtype, device=k.device)
    for t in range(T):
        kt = k[:, t, :]
        vt = v[:, t, :]
        ekt = torch.exp(kt.clamp(min=-60.0, max=60.0))
        state = state * gamma[0, 0, :] + ekt * vt
        denom = denom * gamma[0, 0, :] + ekt
        mix = torch.exp((kt + u[0, 0, :]).clamp(min=-60.0, max=60.0))
        num = state + mix * vt
        den = denom + mix + 1e-6
        y[:, t, :] = num / den
    return y


def forward(B, T, C, w, u, k, v, y):
    res = wkv_forward_fallback(w, u, k, v)
    y.copy_(res)


def backward(B, T, C, w, u, k, v, gy, gw, gu, gk, gv):
    pass
