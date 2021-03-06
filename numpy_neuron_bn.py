from sklearn.model_selection import train_test_split
import time
import numpy as np

np.warnings.filterwarnings('ignore')


class NeuronNet:
    def __init__(self, input_nodes=784,
                 hidden_nodes=200,
                 output_nodes=10):
        self.w_i_h = np.random.randn(input_nodes * hidden_nodes).reshape(input_nodes, hidden_nodes)
        self.b_i_h = np.zeros(shape=(1, hidden_nodes))
        self.w_h_o = np.random.randn(hidden_nodes * output_nodes).reshape(hidden_nodes, output_nodes)
        self.b_h_o = np.zeros(shape=(1, output_nodes))
        self.gamma = np.ones(shape=(1, hidden_nodes))
        self.beta = np.zeros(shape=(1, hidden_nodes))
        self.bn_params = {'bn_mean': 0, 'bn_var': 0}

    def Relu(self, inputs):
        inputs[inputs < 0] = 0
        return inputs

    def input_op(self, inputs):
        """
        输入层的操作
        :param inputs: 输入层的输入
        :return: 输入层的输出
        """
        return inputs

    def hidden_train_op(self, output_i):
        '''
        在训练中隐藏层的操作
        :param inputs: 隐藏层的输入
        :return: 隐藏层的输出
        '''
        inputs_h = output_i.dot(self.w_i_h) + self.b_i_h
        inputs_h, bn_cache, mu, var = self.batchnorm_forward(inputs_h, self.gamma, self.beta)
        hidden_output = self.Relu(inputs_h)
        return hidden_output, bn_cache, mu, var

    def hidden_op(self, output_i):
        """
        在进行测试时隐藏层的操作
        :param output_i: 隐藏层的输入
        :return: 隐藏层的输出
        """
        inputs_h = output_i.dot(self.w_i_h) + self.b_i_h
        output_i = (inputs_h - self.bn_params['bn_mean']) / np.sqrt(self.bn_params['bn_var'] + 1e-8)
        input_h = self.gamma * output_i + self.beta
        hidden_output = self.Relu(input_h)
        return hidden_output

    # 输出层的操作
    def output_op(self, output_h):
        '''
        输出层的操作
        :param inputs: 输出层的输入
        :return: 输出层的输出
        '''
        input_o = np.dot(output_h, self.w_h_o) + self.b_h_o
        output = self.softmax(input_o)
        return output

    def get_io_data(self, inputs):
        """
        返回所有层的输出和一些参数（这些参数是用于之后的bn层的反向传播）
        :param inputs: 样本数据
        :return: 所有层的输出和一些参数
        """
        output_i = self.input_op(inputs)
        output_h, bn_cache, mu, var = self.hidden_train_op(output_i)
        output_o = self.output_op(output_h)
        return output_i, output_h, bn_cache, mu, var, output_o

    def get_io_data_test(self, inputs):
        """
        返回所有层的输出，由于这个方法是用在测试的时候，所以此刻无需返回参数
        :param inputs: 样本数据
        :return: 所有层的输出
        """
        output_i = self.input_op(inputs)
        output_h = self.hidden_op(output_i)
        output_o = self.output_op(output_h)
        return output_i, output_h, output_o

    # 计算梯度
    def gd(self, inputs, y_labels, eta, output_i, output_h, output_o, cache):
        # 求出每个样本标签的one hot编码
        y_one_hot = np.array([[ele == y_label for ele in range(10)] for y_label in y_labels], dtype=int)
        dX, dgamma, dbeta = self.batchnorm_backward(
            ((output_o - y_one_hot).dot(self.w_h_o.T) * (output_i.dot(self.w_i_h) > 0)), cache)
        dw_h_o = (output_o - y_one_hot).T.dot(output_h).T
        db_h_o = np.sum(output_o - y_one_hot, axis=0) / len(output_o)
        dw_i_h = dX.T.dot(output_i).T
        db_i_h = np.sum(dX, axis=0) / len(dX)

        self.w_h_o -= eta * dw_h_o
        self.b_h_o -= eta * db_h_o
        self.w_i_h -= eta * dw_i_h
        self.b_i_h -= eta * db_i_h
        self.gamma -= eta * dgamma
        self.beta -= eta * dbeta

    def batchnorm_backward(self, dout, cache):
        """
        bn层的反向传播
        :param dout:对bn层的输出的偏导
        :param cache:计算时用到的参数，包括样本数据，归一化后的样本数据，反差和均值
        :return:bn层输入的偏导，gamma的偏导和beta的偏导
        """
        X, X_norm, mu, var, gamma, beta = cache

        N, D = X.shape

        X_mu = X - mu
        std_inv = 1. / np.sqrt(var + 1e-8)

        dX_norm = dout * gamma
        dvar = np.sum(dX_norm * X_mu, axis=0) * -.5 * std_inv ** 3
        dmu = np.sum(dX_norm * -std_inv, axis=0) + dvar * np.mean(-2. * X_mu, axis=0)

        dX = (dX_norm * std_inv) + (dvar * 2 * X_mu / N) + (dmu / N)
        dgamma = np.sum(dout * X_norm, axis=0)
        dbeta = np.sum(dout, axis=0)

        return dX, dgamma, dbeta

    def batchnorm_forward(self, X, gamma, beta):
        """
        bn层的正向传播
        :param X: 样本数据
        :return: bn层的输出，反差，均值和方向传播用到的参数
        """
        mu = np.mean(X, axis=0)
        var = np.var(X, axis=0)

        X_norm = (X - mu) / np.sqrt(var + 1e-8)
        out = gamma * X_norm + beta

        cache = (X, X_norm, mu, var, gamma, beta)

        return out, cache, mu, var

    def softmax(self, x):
        x -= np.max(x, axis=1, keepdims=True)  # 为了稳定地计算softmax概率， 一般会减掉最大的那个元素
        x = np.exp(x) / np.sum(np.exp(x), axis=1, keepdims=True)
        return x

    def mini_train(self, inputs, y_labels, eta, n_iters, batch_size):
        """
        训练过程
        :param inputs: 样本数据
        :param y_labels: 样本标签
        :param eta: 学习率
        :param n_iters: 循环整体样本的次数
        :param batch_size: 子样本的大小
        :return: None
        """
        # 求出整体样本呢可以分成几个子样本
        batch_times = len(inputs) // batch_size + 1
        step = 1
        for _ in range(n_iters):
            self.shuffle(inputs, y_labels)
            for i in range(batch_times):
                # 获取子样本
                if (i + 1) == batch_times:
                    mini_batch = inputs[self.index(i, batch_size):]
                    mini_labels = y_labels[self.index(i, batch_size):]
                else:
                    mini_batch = inputs[self.index(i, batch_size):self.index(i + 1, batch_size)]
                    mini_labels = y_labels[self.index(i, batch_size):self.index(i + 1, batch_size)]

                y_one_hot = np.array([[ele == y_label for ele in range(10)] for y_label in mini_labels])
                output_i, output_h, bn_cache, mu, var, output_o = self.get_io_data(mini_batch)
                score_mini = self.score(mini_batch, mini_labels)
                # 接下来的式子求出来的值将作为 最后进行训练时不变的均值和方差
                self.bn_params['bn_mean'] = .9 * self.bn_params['bn_mean'] + .1 * mu
                self.bn_params['bn_var'] = .9 * self.bn_params['bn_var'] + .1 * var
                # 使用交叉熵作为损失函数
                loss_mini = -np.sum(np.sum(y_one_hot * np.log(output_o), axis=1), axis=0) / len(mini_labels)

                self.gd(mini_batch, mini_labels, eta, output_i, output_h, output_o, bn_cache)
                print("step: {0}, score: {1}, loss_mini: {2}".format(step, score_mini, loss_mini))
                step += 1

    def index(self, x, batch_size):
        assert x >= 0
        return batch_size * x

    def predict(self, inputs):
        """
        对输入的样本做出一个预测
        :param inputs: 样本数据
        :return: 预测的样本标签
        """
        res = []
        output_i, output_h, output_o = self.get_io_data_test(inputs)
        for output in output_o:
            res.append(np.argmax(output))
        return res

    def score(self, inputs, y_labels):
        """
        对样本的预测输出计算准确率
        :param inputs: 样本数据
        :param y_labels: 样本标签
        :return: 准确率
        """
        y_outputs = self.predict(inputs)
        comparison = [y_output == y_label for y_output, y_label in zip(y_outputs, y_labels)]
        return sum(comparison) / len(comparison)

    def shuffle(self, inputs, y_labels):
        """
        打乱样本数据和样本标签
        :param inputs: 样本数据
        :param y_labels: 样本标签
        :return: 打乱后的样本数据和标签
        """
        index = np.arange(len(inputs))
        np.random.shuffle(index)
        return inputs[index], y_labels[index]


nn = NeuronNet()
# 导入数据，该样本共有110000
from tensorflow.examples.tutorials.mnist import input_data
# 使用改代码时，需修改一下图片导入的路径
data = input_data.read_data_sets('../dataset/fashion')
(inputs, y) = data.train.next_batch(1000000)

# 将样本数据变到0-1之间，便于后面的计算
# 选择0.01作为范围最低点，是为了避免0值输入最终会人为地造成权重更新失败（来自python神经网络编程）
inputs = (inputs / 255 * 0.99) + 0.01

# 将数据集分成训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(inputs, y, test_size=0.3)
# 开始训练、测试并计时
start_time = time.clock()
nn.mini_train(X_train, y_train, 0.005, 8, 256)
score = nn.score(X_test, y_test)
print("测试集的分数为：{0}".format(score))
print("train and test time={0}".format(time.clock() - start_time))


