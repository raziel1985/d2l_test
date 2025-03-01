import torch

# 多通道输入
def corr2d(X, K):
    h, w = K.shape
    Y = torch.zeros((X.shape[0] - h + 1, X.shape[1] - w + 1))
    for i in range(Y.shape[0]):
        for j in range(Y.shape[1]):
            Y[i, j] = (X[i:i+h, j:j+w] * K).sum()
    return Y

def corr2d_multi_in(X, K):
    return sum(corr2d(x, k) for x, k in zip(X, K))

X = torch.tensor([[[0.0, 1.0, 2.0], [3.0, 4.0, 5.0], [6.0, 7.0, 8.0]],
                  [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]])
K = torch.tensor([[[0.0, 1.0], [2.0, 3.0]], [[1.0, 2.0], [3.0, 4.0]]])
print(corr2d_multi_in(X, K))

# 多通道输出
def corr2d_multi_out(X, K):
    return torch.stack([corr2d_multi_in(X, k) for k in K], 0)

print(K.shape)
K = torch.stack((K, K+1, K+2), 0)
print(K.shape)
print(corr2d_multi_out(X, K))   # 输出通道3， 输入通道2， 长宽2*2

# 1*1卷积层 (没有空间信息，只做通道间的融合）
def corr2d_multi_in_out_1x1(X, K):
    c_i, h, w = X.shape
    c_o = K.shape[0]
    X = X.reshape((c_i, h*w))
    K = K.reshape(c_o, c_i)
    Y = torch.matmul(K, X)
    return Y.reshape((c_o, h, w))

X = torch.normal(0, 1, (3, 3, 3))
K = torch.normal(0, 1, (2, 3, 1, 1))
Y1 = corr2d_multi_in_out_1x1(X, K)
print(Y1.shape)
Y2 = corr2d_multi_out(X, K)
print(Y2.shape)
print(float(torch.abs(Y1 - Y2). sum()))
