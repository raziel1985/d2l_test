import common
import torch
import matplotlib.pyplot as plt
from torch import nn

#############
# 从零开始实现
#############
batch_size, num_steps = 32, 35
train_iter, vocab = common.load_data_time_machine(batch_size, num_steps)

# 初始化模型参数
def get_params(vocab_size, num_hiddens, device):
    num_inputs = num_outputs = vocab_size

    def normal(shape):
        return torch.randn(size=shape, device=device) * 0.01

    def three():
        return (normal((num_inputs, num_hiddens)),
                normal((num_hiddens, num_hiddens)),
                torch.zeros(num_hiddens, device=device))

    W_xz, W_hz, b_z = three()   # 更新门参数
    W_xr, W_hr, b_r = three()   # 重置门参数
    W_xh, W_hh, b_h = three()   # 候选隐藏状态参数
    # 输出层参数
    W_hq = normal((num_hiddens, num_outputs))
    b_q = torch.zeros(num_outputs, device=device)
    # 附加梯度
    params = [W_xz, W_hz, b_z, W_xr, W_hr, b_r, W_xh, W_hh, b_h, W_hq, b_q]
    for param in params:
        param.requires_grad_(True)
    return params

# 定义模型
def init_gru_state(batch_size, num_hiddens, device):
    return (torch.zeros((batch_size, num_hiddens), device=device), )

def gru(inputs, state, params):
    W_xz, W_hz, b_z, W_xr, W_hr, b_r, W_xh, W_hh, b_h, W_hq, b_q = params
    H, = state
    outputs = []
    for X in inputs:
        Z = torch.sigmoid((X @ W_xz) + (H @ W_hz) + b_z)
        R = torch.sigmoid((X @ W_xr) + (H @ W_hr) + b_r)
        H_tilda = torch.tanh((X @ W_xh) + ((R * H) @ W_hh) + b_h)
        H = Z * H + (1 - Z) * H_tilda
        Y = H @ W_hq + b_q
        outputs.append(Y)
    return torch.cat(outputs, dim=0), (H,)

# 训练与预测
vocab_size, num_hiddens, device = len(vocab), 256, common.try_gpu()
num_epochs, lr = 500, 1

model = common.RNNModelScratch(len(vocab), num_hiddens, device, get_params, init_gru_state, gru)
common.train_ch8(model, train_iter, vocab, lr, num_epochs, device)
plt.show()


#############
# 简洁实现
#############
num_inputs = vocab_size
gru_layer = nn.GRU(num_inputs, num_hiddens)
model = common.RNNModel(gru_layer, len(vocab))
model = model.to(device)
common.train_ch8(model, train_iter, vocab, lr, num_epochs, device)
plt.show()
