import common
import matplotlib.pyplot as plt
import torch
import torchvision
from torch import nn
from d2l import torch as d2l

# 读取内容和风格图像
content_img = d2l.Image.open('../img/rainier.jpg')
plt.imshow(content_img)
plt.show()

style_img = d2l.Image.open('../img/autumn-oak.jpg')
plt.imshow(style_img)
plt.show()

# 预处理和后处理
rgb_mean = torch.tensor([0.485, 0.456, 0.406])
rgb_std = torch.tensor([0.229, 0.224, 0.225])

def preprocess(img, image_shape):
    transforms = torchvision.transforms.Compose([
        torchvision.transforms.Resize(image_shape),
        torchvision.transforms.ToTensor(),
        torchvision.transforms.Normalize(mean=rgb_mean, std=rgb_std)])
    return transforms

def postprocess(img):
    img = img[0].to(rgb_std.device)
    img = torch.clamp(img.permute(1, 2, 0) * rgb_std + rgb_mean, 0, 1)
    return torchvision.transforms.ToPILImage()(img.permute(2, 0, 1))

# 抽取图像特征
# TODO(rogerluo): 预训练模型下载失败
pretrained_net = torchvision.models.vgg19(pretrained=True)
# TODO(rogerluo): 为什么内容只取一层，而样式取这么多层。是因为初始图就是内容图片吗？
style_layers, content_layers = [0, 5, 10, 19, 28], [25]
# 保留vgg中，从输入层到最靠近输出层的内容或风格层中的所有层
net = nn.Sequential(*[pretrained_net.features[i] for i in range(max(content_layers + style_layers) + 1)])

def extract_features(X, content_layers, style_layers):
    contents = []
    styles = []
    for i in range(len(net)):
        X = net[i](X)
        if i in style_layers:
            styles.append(X)
        elif i in content_layers:
            contents.append(X)
    return contents, styles

def get_content(image_shape, device):
    content_X = preprocess(content_img, image_shape).to(device)
    contents_Y, _ = extract_features(content_X, content_layers, style_layers)
    return content_X, contents_Y

def get_style(image_shape, device):
    style_X = preprocess(style_img, image_shape).to(device)
    _, styles_Y = extract_features(style_X, content_layers, style_layers)
    return style_X, styles_Y

# 定义损失函数
def content_loss(Y_hat, Y):
    return torch.square(Y_hat - Y.detach()).mean()

def gram(X):
    # 协方差：描述数值的分布
    num_channels, n = X.shape[1], X.numel() // X.shape[1]
    X = X.reshape((num_channels, n))
    return torch.matmul(X, X.T) / (num_channels * n)

def style_loss(Y_hat, gram_Y):
    return torch.square(gram(Y_hat) - gram_Y.detach()).mean()

def tv_loss(Y_hat):
    # 降噪：像素和周围像素的绝对值差异尽量小
    return 0.5 * (torch.abs(Y_hat[:, :, 1, :] - Y_hat[:, :, -1:, :]).mean() +
                  torch.abs(Y_hat[:, :, :, 1] - Y_hat[:, :, :, -1]).mean())

content_weight, style_weight, tv_weight = 1, 1e3, 10

def compute_loss(X, contents_Y_hat, styles_Y_hat, contents_Y, styles_Y_gram):
    contents_l = [content_loss(Y_hat, Y) * content_weight for Y_hat, Y in zip(contents_Y_hat, contents_Y)]
    styles_l = [style_loss(Y_hat, Y) * style_weight for Y_hat, Y in zip(styles_Y_hat, styles_Y_gram)]
    tv_l = tv_loss(X) * tv_weight
    l = sum(10 * styles_l + contents_l + [tv_l])
    return contents_l, styles_l, tv_l, l

# 初始化合成图片
class SynthesizedImage(nn.Module):
    def __init__(self, img_shape, **kwargs):
        super(SynthesizedImage, self).__init__(**kwargs)
        self.weight = nn.Parameter(torch.rand(*img_shape))

    def forward(self):
        return self.weight

def get_inits(X, device, lr, styles_Y):
    gen_img = SynthesizedImage(X.shape).to(device)
    gen_img.weight.data.copy_(X.data)
    trainer = torch.optim.Adam(gen_img.parameters(), lr=lr)
    styles_Y_gram = [gram(Y) for Y in styles_Y]
    return gen_img(), styles_Y_gram, trainer

# 训练模型
def train(X, contents_Y, styles_Y, device, lr, num_epochs, lr_decay_epoch):
    gen_img = SynthesizedImage(X.shape).to(device)
    gen_img.weight.data.copy_(X.data)
    img = gen_img()
    trainer = torch.optim.Adam(gen_img.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(trainer, lr_decay_epoch, 0.8)
    animator = d2l.Animator(xlabel='epoch', ylabel='loss', xlim=[10, num_epochs],
                            legend=['content', 'style', 'TV'], ncols=2, figsize=(7, 2.5))
    styles_Y_gram = [gram(Y) for Y in styles_Y]
    for epoch in range(num_epochs):
        trainer.zero_grad()
        contents_Y_hat, styles_Y_hat = extract_features(img, content_layers, style_layers)
        contents_l, styles_l, tv_l, l = compute_loss(img, contents_Y_hat, styles_Y_hat,
                                                     contents_Y, styles_Y_gram)
        l.backward()
        trainer.step()
        scheduler.step()
        print(epoch + 1, float(sum(contents_l)), float(sum(styles_l)), float(tv_l))
        if (epoch + 1) % 10 == 0:
            animator.axes[1].imshow(postprocess(img))
            animator.add(epoch + 1, [float(sum(contents_l)), float(sum(styles_l)), float(tv_l)])
            plt.show()
    return img

device, image_shape = common.try_gpu_or_mps(), (300, 450)
net = net.to(device)
content_X, contents_Y = get_content(image_shape, device)
print(content_X.shape, contents_Y.shape)
_, styles_Y = get_style(image_shape, device)
print(styles_Y.shape)
output = train(content_X, contents_Y, styles_Y, device, 0.3, 500, 50)
plt.imshow(postprocess(output))
plt.show()