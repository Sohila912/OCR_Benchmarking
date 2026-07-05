Improving the Learning of Multi-column Convolutional Neural.
Network for Crowd Counting
Zhi-Qi Cheng1,2*, Jun-Xiu Lil,3*, Qi Dai3, Xiao Wu1t, Jun-Yan He1, Alexander G. Hauptmann?.
1Southwest Jiaotong University, 2Carnegie Mellon University, Microsoft Research
{zhiqic,alex}@cs.cmu.edu,{lijunxiu@my, wuxiaohk@home}.swjtu.edu.cn, qid@microsoft.com,junyanhe1989@gmail.com
ABSTRACT
Tremendous variation in the scale of people/head size is a critical
6
problem for crowd counting. To improve the scale invariance of
feature representation, recent works extensively employ Convo-
lutional Neural Networks with multi-column structures to handle
2
different scales and resolutions. However, due to the substantial re-
 dundant parameters in columns, existing multi-column networks in-
Figure 1: Examples of ShanghaiTech Part A dataset [69]. Crowd
variably exhibit almost the same scale features in different columns,
S
counting is a challenging task with the significant variation in the
which severely affects counting accuracy and leads to overfitting
 people/head size due to the perspective effect..
7
In this paper, we attack this problem by proposing a novel Multi
 INTRODUCTION
column Mutual Learning (McML) strategy. It has two main innova-
tions: 1) A statistical network is incorporated into the multi-column
With the growth of wide applications, such as safety monitoring,
framework to estimate the mutual information between columns,
disaster management, and public space design, crowd counting has
which can approximately indicate the scale correlation between
been extensively studied in the past decade. As shown in Figure 1, a
features from different columns. By minimizing the mutual infor-
significant challenge of crowd counting lies in the extreme variation
mation, each column is guided to learn features with different
in the scale of people/head size. To improve the scale invariance
image scales. 2) We devise a mutual learning scheme that can al-
 of feature learning, Multi-column Convolutional Neural Networks
ternately optimize each column while keeping the other columns
are extensively studied [3, 12, 21, 32, 44, 50, 69]. As illustrated in
fixed on each mini-batch training data. With such asynchronous
Figure 2, the motivation of multi-column networks is intuitive. Each
.07608v1
parameter update process, each column is inclined to learn different
column is devised with different receptive fields (e.g., different filter
feature representation from others, which can efficiently reduce the
sizes) so that the features learned by different columns are expected
to focus on different scales and resolutions. By assembling features
remarkably, McML can be applied to all existing multi-column
from all columns, multi-column networks are easily adaptive to the
networks and is end-to-end trainable. Extensive experiments on
four challenging benchmarks show that McML can significantly
scales and resolutions.
6061
improve the original multi-column networks and outperform the
Although multi-column architecture is naturally employed for
other state-of-the-art approaches.
addressing the issue of various scale change, previous works [12,
21, 30, 44, 62] have pointed out that different columns always gen-
KEYWORDS
erate features with almost the same scale, which indicates that
V:
Crowd Counting; Multi-column Network; Mutual Learning Strategy
existing multi-column architectures cannot effectively improve the
scale invariance of feature learning. To further verify this observa-
X
ACM Reference Format:
tion, we have extensively analyzed three state-of-the-art networks,
Zhi-Qi Cheng, Jun-Xiu Li, Qi Dai, Xiao Wu, Jun-Yan He, Alexander G. Haupt-
i.e., MCNN [69], CSRNet [30] and ic-CNN [44]. It is worth noting
mann. 2019. Improving the Learning of Multi-column Convolutional Neural
that CSRNet is a single column network, which has four different
Network for Crowd Counting. In Proceedings of the 27th ACM International
configurations (i.e., different dilation rates). We remould CSRNet
Conference on Multimedia (MM '19), Oct. 21-25, 2019, Nice, France. ACM,
to treat each configuration as a column, and design a four-column
New York, NY, USA, 11 pages. https://doi.org/10.1145/3343031.3350898
network as an alternative. The Maximal Information Coefficient
(MIC)' and the Structural SIMilarity (SSIM)? are computed based on
*Equal contribution. This work was done when Zhi-Qi Cheng and Jun-Xiu Li visited
at Microsoft Research. 'Xiao Wu is the corresponding author..
the results of different columns. MIC measures the strength of asso-
Permission to make digital or hard copies of all or part of this work for personal or
ciation between the outputs (i.e., crowd counts) and SsIM measures
classroom use is granted without fee provided that copies are not made or distributed
the similarity between density maps. As shown in Table 1, different
for profit or commercial advantage and that copies bear this notice and the full citation
 on the first page. Copyrights for components of this work owned by others than ACM
columns (Col.<>Col.) always output almost the same counts (i.e.,
must be honored. Abstracting with credit is permitted. To copy otherwise, or republish
high MIC) and the similar estimated density maps (i.e., high SsIM)
 to post on servers or to redistribute to lists, requires prior specific permission and/or a.
In contrast, a large gap between the ensemble of all columns and
fee. Request permissions from permissions@acm.org..
MM '19, October 21-25, 2019, Nice, France
the ground truth (Col.<>GT.) still exists. This comparison shows
 2019 Association for Computing Machinery
ACM ISBN 978-1-4503-6889-6/19/10... $15.00
1https://en.wikipedia.org/wiki/Maximal_information_coefficient.
https://doi.org/10.1145/3343031.3350898
2https://en.wikipedia.org/wiki/Structural_similarity
Table 1: The result analysis of three multi-column networks. The
learn features with different scales and how to reduce the enormous
values in the table are the average of all columns. Col.>Col. is the
redundant parameters and avoid overfitting, which are problems
result between different columns. Col.<>GT is the result between
not yet fully understood in the literature..
the ensemble of all columns and the ground truth.
Col.> Col.
Col.> GT
2 RELATED WORK
 Method
MIC SSIM
MIC
SSIM
2.1 Detection-based Methods
ShanghaiTech Part A [69]
MCNN [69]
0.55
0.94
0.71
0.52
These models use visual object detectors to locate people in images.
CSRNet [30]
0.93
0.84
0.74
0.71
Given the individual localization of each people, crowd counting
ic-CNN [44]
0.70
0.68
UCF_CC_50 [24]
becomes trivial. There are two directions in this line, i.e., detection
on 1) whole pedestrians [4, 16, 58, 70] and 2) parts of pedestrians
MCNN [69]
0.70
0.36
0.81
CSRNet [30]
0.71
0.48
[17, 25, 31, 61]. Typically, local features [16, 31] are first extracted
0.87
0.72
ic-CNN [44]
0.57
0.52
and then are exploited to train various detectors (e.g., SVM [31]
and AdaBoost [59]). Although these works achieve satisfactory
that there are substantial redundant parameters among columns,
results for the low-density scenario, they are unable to generalize
which makes multi-column architecture fails to learn the features
for high-density images since it is impossible to train a detector for
across different scales. On the other hand, it indicates that existing
extremely crowded scenes..
multi-column networks tend to overfit the data and can not learn
the essence of the ground truth.
2.2 Regression-based Methods
Inspired by previous works [30, 44, 62], we reveal that the prob-
Different from detection-based models, regression-based methods
lem of existing multi-column networks lies in the difficulty of learn
directly estimate crowd count using image features. It has two
ing features with different scales. Generally speaking, there are
steps: 1) extract powerful image features, 2) use various regression
two main problems: 1) There is no supervision to guide multiple
models to estimate the crowd count. Specifically, image features
columns to learn features at different scales. The current learning
objective is only to minimize the errors of crowd count. Although
11, 24, 43]. Regression methods cover Bayesian [9], Ridge [11],
we have designed different columns to have different receptive
Forest [43] and Markov Random Field [24, 41]. Since these works
fields, they are still gradually forced to generate features with al-
always use handcrafted low-level features, they still cannot obtain
most the same scale along with the network optimization. 2) There
satisfactory performance.
are huge redundant parameters among columns. Because of parallel
2.3CNN-based Methods
column architectures, multi-column networks naturally brought in
redundant parameters. As the analysis of [1], with the increase of
Due to substantial variations in the scale of people/head size, most
parameters, a more substantial amount of training data is also re.
recent studies extensively use Convolutional Neural Networks
(CNN) with multi-column structures for crowd counting. Specifi-
harder to train and easier to overfit..
cally, a dual-column network is proposed by [3] to merge shallow
In this paper, we propose a novel Multi-column Mutual Learning
and deep layers to estimate crowd counts. Inspired by this work.
(McML) strategy to improve the learning of multi-column networks.
a great three-column network named MCNN is proposed by [69],
As illustrated in Figure 3, our McML addresses the above two issues
which employs different filters on separate columns to obtain the
from two aspects. 1) A statistical network is proposed to measure
various scale features. Noted that there are a lot of works to con-
the mutual information between different columns. The mutual
tinually improve MCNN [26, 55, 56, 60]. Sam et al. [50] introduce a
information can approximately measure the scale correlation be-
switching structure, which uses a classifier to assign input image
 tween features from different columns. By additionally minimizing
patches to best column structures. Recently, Liu et al. [32] propose
the mutual information in the loss, different column structures
a multi-column network to simultaneously estimate crowd density
are forced to learn feature representations with different scales.
by detection and regression models. Ranjan et al. [44] employ a
2) Instead of the conventional optimization that updates the pa-
two-column structure to iterative train their model with different
rameters of multiple columns simultaneously, we devise a mutual
resolution images.
 learning scheme that can alternately optimize each column while
 In addition to multi-column networks, there are a lot of methods
keeping the other columns fixed on each mini-batch training data
to improve scale invariance of feature learning by 1) studying on the
With such asynchronous learning steps, each column is inclined
fusion of multi-scale features [35, 57, 62, 63], 2) studying on multi-
to learn different feature representation from others, which can
blob based scale aggregation networks [7, 64], 3) designing scale-
efficiently reduce the parameter redundancy and improve the gener.
invariant convolutional or pooling layers [21, 30, 33, 56, 62], and
alization ability. The proposed McML can be applied to all existing
4) studying on automated scale adaptive networks [48, 49, 66]. On
multi-column networks and is end-to-end trainable. We conduct
the other hand, a lot of studies devote to using perspective maps [52],
extensive experiments on four datasets to verify the effectiveness
geometric constraints [34, 68], and region-of-interest [33] to further
of our method.
improve the counting accuracy..
The main contribution of this work is the proposal of Multi-
These state-of-the-art methods aim to improve the scale invari-
column Mutual Learning (McML) strategy to improve the learning
ance of feature learning. Inspired by recent studies [30, 44, 62], we
 of multi-column networks. The solution also provides the elegant
reveal that existing multi-column networks cannot effectively learn
views of how to explicitly supervise multi-column architectures to
different scale features as Sec. 1. To solve this problem, we propose
a typical multi-column network named MCNN [69]. The intentions
of multi-column networks are natural, where each column structure
is devised with different receptive fields (e.g., different filter sizes)
so that the features learned by individual column is expected to
focus on a particular scale of people/head size. With the ensemble
of features from all columns, multi-column networks are easily
adaptive to handle the large scale variations.
Although the motivation for multi-column structures is straight-
Figure 2: The architecture of MCNN [69]. It is a classical Multi
forward, previous works [30, 44, 62] have pointed out that existing
column Convolutional Neural Network. It employs different size of
multi-column networks cannot improve the scale invariance of
 filters on three columns to obtain different scale features.
features learning. As analyzed in Sec. 1, we are convinced that
there are abundant redundant parameters between columns, which.
 a novel Multi-column Mutual Learning (McML) strategy, which can
causes multi-column structures to fail to learn the features across
be applied to all existing CNN-based multi-column networks and is
different scales and invariably get almost the same estimated crowd
end-to-end trainable. It is noted that the previous work ic-CNN [44]
counts and density maps. After thoroughly surveying previous.
also proposes an iterative learning strategy to improve the learning
works [30, 44, 46, 62, 67] and analyzing our experimental results in
of multi-column networks. Different from our McML, since ic-CNN
is designed for a specific neural architecture, it can not be gener-
Table 1, we further reveal that the main problem of existing multi-
column networks lies in the learning process. Generally speaking,.
alized to all multi-column networks. Additionally, we have tested
current learning strategy has two main weaknesses. 1) It only opti-
our McML on the same network of ic-CNN. Experimental results
mizes the objective of crowd counting, while completely ignores
show that McML can still significantly improve the performance of
the intention of using multi-column structures to learn different
the original ic-CNN.
scale features. 2) It instantly optimizes multi-column structures at
the same time, which can result in the enormous redundant param-
3  MULTI-COLUMN MUTUAL LEARNING
eters among columns and overfitting on the limited training data.
In this section, we present the proposed Multi-column Mutual
To address these problems, our work aims to propose a general.
Learning (McML) strategy. The problem formulation is first in-
learning strategy named Multi-column Mutual learning (McML) to
troduced in Sec. 3.1. Then the overview of our McML is described
improve the learning of multi-column networks.
in Sec. 3.2. More details of McML are illustrated in Sec. 3.3 to 3.5.
3.1 Problem Formulation
3.2Overview of McML
Recent studies define crowd counting task is as a density regression
In this section, we present an overview of Multi-column Mutual.
problem [7, 29, 69]. Given N training images X = {1, :-- , xN} as
Learning (McML) strategy. For the sake of simplicity, we introduce
the training set, each image x; is annotated with a total of c; center
the case of two columns as an example. As shown in Figure 3, our
McML has two main innovations..
ground truth density map yi of image x; is generated as,
: McML has integrated a statistical network into multi-column
Vp Exi,yi= N9t(p;=P,o2),
(1)
structures to automatically estimate the mutual information
Pepgt
between columns. The essential of the statistical network is
where p is a pixel and Ngt is a Gaussian kernel with standard
a classifier network. Specifically, the inputs are features from
deviation o. The number of people c; in image xi is equal to the
different columns, and the output is the mutual information
sum of density of all pixels as pex; yi(p) = cj. With these training
between columns. We use mutual information to approxi-
data, crowd counting models aim to learn a regression model G
mately indicate the scale correlation between features from
with parameters 0 to minimize the difference between estimated
different columns. By minimizing the mutual information
density map G(xi) and ground truth density map Y;. Specifically
between columns, McML can guide each column to focus on
Euclidean distance, i.e., L2 loss is employed to get an approximate
different image scale information..
solution,
. McML is a mutual learning scheme. Different from updating
1
N
the parameters of multiple columns simultaneously, McMI
(Gg(xi)-yi)2,
L2 =
(2)
alternately optimizes each column in turn until the network
2N 
where as the size of input images are different, the value of Eqn. 2
converged. In the learning of each column, the mutual infor-
 is further normalized by the number of pixels in each image.
mation between columns is first estimated as prior knowl-
edge to guide the parameter update. With the help of the
It is noted that, as shown in Figure 1, enormous variation in the
 scale of people/head size is a critical problem for crowd counting.
mutual information between columns, McML can alternately
Many studies [5, 13, 19, 22, 46, 67] have proved that only using
make each column to be guided by other columns to learn
different image scales/resolutions. It is proved that this mu-
an individual regression model is theoretically far from the global
optimal. To improve the scale invariance of feature learning, Convo-
tual learning scheme can significantly reduce the volume of
redundant parameters and avoid overfitting.
lutional Neural Networks with multi-column structures are exten.
sively studied by recent works [26, 55, 56, 60, 69]. Figure 2 illustrates
Column 01
Conv7-32
Conv9-1
Conv7-8
Statistical Network
FC-128
-C-
Conv7-20
Conv5-20
Conv5-10
Maxpool
Maxpoo
Concatenate
Column 02
Figure 3: Overview of our Multi-column Mutual Learning (McML) strategy. It is equivalent to adding a statistical network to estimate the
mutual information I, between columns. By minimizing the mutual information, it can guide multi-columns to learn different scale infor-
mation. Additionally, McML is a mutual learning scheme as arrows  and , where each column is alternately optimized while keeping the
other columns fixed on each mini-batch training data. Specifically, this is an example of two columns (O1 and O2) in MCNN [69]. ConvX-Y
implies a convolution layer has Y filters with XX kernel size. The stride of all convolutional layers is 1, except for the special reminder.
MaxPool is the max pooling layer with a stride of 2. [Best viewed in color].
Mathematically, two columns with parameters 01 and 02 are
3.3  Mutual Information Estimation
alternately trained as,
In this section, we first briefly introduce the definition of mutual
information. Then we present the statistical network in details.
Lo, = minL2(Conv(Feo02(X), Y) + I(Co;Ce2),
(3)
 Mutual information is a fundamental quantity for measuring the
correlation between variables. We treat column structures as dif-
Le2 = minL2(Conv(Fe,oe(X)), Y) + aI(C;Co2),
(4)
ferent variables. Inspired by the success of previous works [28, 38],
02
we use mutual information to indicate the degree of parameter
where each column is trained by two losses. L2 loss (Eqn. 2) is
redundancy between columns. Moreover, mutual information can
used to minimize counting errors, and I (Eqn. 7) is employed
also approximately measure the scale correlation between features
to minimize the mutual information between columns. a is the
from different columns. Instead of estimating the mutual informa-
weight to trade off two losses. The value of mutual information I
tion with parameters of columns, similar to [6, 15, 20], we chooses
is computed by the statistical network with parameters w. Here
to compute the mutual information using the features of multi
we have slightly abused symbols. Co, and Co, are features from
columns since our objective is to learn different scale features.
different convolutional layers of two columns, which are used to
Typically, the mutual information between features Ce, and Ce, is
 defined as,
estimate the mutual information. Feo,(X) means the ensemble
(i.e., concatenation) of features at the last convolutional layers for
I(C,;Ce,) := H(Ce) - H(Ce,| Co),
(5)
two both columns. Conv is a 1  1 convolutional layer that is used
to predict density maps for crowd counting..
where H is the Shannon entropy. H(Ce, | Co,) measures the uncer-
Typically, our proposed McML is also a mutual learning scheme.
tainty in Co, given Cg2. Previous works [6, 28, 38, 42] widely use
Two columns are alternately optimized until convergence. In the
Kullback-Leibler (KL) divergence to compute the mutual informa
learning of each column, the mutual information Io is first esti
tion,
mated as prior knowledge to guide the parameter update. Once the
I(Co;Co) =DKL(PCoCo2|| Pco 0PCo2),
(6)
optimization of one column (e.g., 0) is finished, we will update the
where PCo Co, is the joint distribution of two features. Pco, and
mutual information I again and alternately to update the other
PCo, are the marginal distributions.  means the production. Since
column (e.g., 02). Additionally, it is noted that Eqns. 3 and 4 show the
situation of most multi-column networks (e.g., CrowdNet [3], AM-
tions Pce, O Pco, are unknown in our case, the mutual information
are concatenated to estimate density maps. However, a few multi
of two columns is challenging to compute [40]
column networks (e.g., ic-CNN [44]) predict density maps in all
Fortunately, inspired by the previous work named MINE [2], we
columns. In these cases, Fe100, of Eqns. 3 and 4 should be replaced
propose a statistical network to estimate the mutual information
with Fe, and Fo, respectively. Where Fe, and Fe, are features from
The essence of the statistical network is a classifier. It can be used
the last convolutional layers at two columns.
to distinguish the samples between the joint distribution and the
Specifically, we will introduce the mutual information estimation
product of marginal distributions. Instead of computing Eqn. 6, the
(i.e., computation of I) in Sec. 3.3, the mutual learning scheme in
statistical network chooses to use Donsker-Varadhan representa-
Sec. 3.4 and neural architectures of statistical networks in Sec. 3.5.
tion [18] i.e., I(Ce,; Ce,)  I(Ce,; Ce,), to get a lower-bound for
Algorithm 1 Mutual Information Estimation
Algorithm 2 Mutual Learning Scheme.
Input: Randomly sampled b images.
Input: Training set X, Ground truth Y.
1: Draw features from two columns as the joint distribution,
1: 01, 02 and w  initialize network parameters;
2: repeat
3: Randomly disrupt Co, as the product of marginal distribution,
 Randomly sampled b images from X;
Estimate mutual information I and update statistical network T
as Alg. 1;
5: Evaluate mutual information I, Das Eqn. 7;.
Update column 01 as Eqn. 3 on each image,
6: Use moving average to get the gradient,
7: G(@)VIw;
Estimate mutual information I and update statistical network T
7:
8: Update the statistical network parameters,.
9: w w+G(w);
as Alg. 1;
Update column 02 as Eqn. 4 on each image,
aL02
the mutual information estimation,.
 10: until Convergence
Io
(7
column Ok is computed as,.
b Z
=1
where To is the statistical network with parameters w. To com-
pute the lower-bound I w, we randomly select b training images.
Io(Co; Cox).
Lgz = L2(Conv(Fe,o02,.,9k(X)), Y) +
With the forward pass of the network, we directly get b pairs
l=1,k#l
of features from two column structures as the joint distribution
(8)
(Co,, Co,) ~ PCo, Co,. At the same time, we randomly disrupt the
order of C, in (C, Ce2) ~ PCe Ce, to get b pairs of features as
concanation) of features from the last convolutional layers at multi-
the product of the marginal distribution (Co, Co2) ~ Pco, @ PCo2
columns. Ce. is the features from different convolutional layers at
Then we input these features to the statistical network To. By cal-
each column. a is a weight to trade off two losses. At this point,
culating the b outputs of the statistical network as Eqn. 7, we can
we only need to add more steps to estimate mutual information
get a lower-bound for the mutual information estimation. Here we
of multi-columns. Once the mutual information is obtained, multi-
use moving average to get the gradient of Eqn. 7. By maximizing
column structures are still alternately optimized until convergence.
this lower-bound, we can approximately obtain the real mutual
information. More details of the mutual information estimation are
3.5 Network Architectures
provided in Alg. 1..
We employ McML to improve three state-of-the-art networks, in
Without loss of generality, the statistical network Tw can be
cluding MCNN [69], CSRNet [30], and ic-CNN [44]. Table 2 shows
 designed as any classifier networks according to the different multi-
the neural architecture of statistical networks. To better under-
column networks. We have tested McML on three multi-column
stand the details, Figure 3 gives a real example of two columns in
networks (i.e., MCNN [69], CSRNet [30] and ic-CNN [44]). The
MCNN [69]. With sharing the parameters, no matter how many
 statistical networks for these baselines are described in Sec. 3.5.
columns are adopted, each multi-column network only needs one
single statistical network. The inputs of statistical networks are the
3.4 Mutual Learning Scheme
features from different layers. We use convolutional layers with
Our proposed McML is a mutual learning scheme. For the sake of
one output channel to reduce the feature dimension. Since training
simplicity, we present the case of two columns as an example. As
images have different size and inspired by the previous work [14],
shown in Alg. 2, we alternately optimize two columns in each mini-
one spatial pyramid pooling (SPP) layer is applied to reshape the
batch until convergence. In each learning iteration, we randomly
features from the last convolutional layer into a fixed dimension.
sample b training images. Before optimizing column O1, the mutual
 information is first estimated as prior knowledge to guide the pa-
Table 2: The structure of statistical network. The convolutional,
rameter update. With forward of the network, the features of two
spatial pyramid pooling, and fully connected layers are denoted as
 column structures are sampled to update the statistical network To
"Conv (kernel size)-(number of channels)-(stride)", "SPP (size of out-
and estimate the mutual information Io as Alg. 1. With the guid-
puts)", and "FC (size of outputs)".
ance of the mutual information, our McML can supervise column 01
MCNN [69]
CSRNet [30]
ic-CNN [44]
to learn as much as possible different scale features from column 02
Conv 5-1-2
Conv 3-1-1
Conv 3-1-1
It is noted that we have fixed parameters of other columns (i.e., 02)
Conv 3-1-2
Conv 3-1-1
Conv 3-1-1
and statistical network (T), and only update column 0. Since the
Conv 3-1-1
Conv 3-1-1
Conv 3-1-1
size of input images are different, we have to update column struc
Conv 3-1-1
Conv 3-1-1
Conv 3-1-1
SPP 256
ture on each image. After back-propagation of a total of b images,
Conv 3-1-1
Conv 3-1-1
FC 128
Conv 3-1-1
SPP 256
the column 02 will be optimized in similar steps.
SPP 256
FC 1
FC 128
It is noted that our McML can be naturally extended to multi-
FC 128
 FC 1
columns architectures. For the case of K > 2, the loss function of a
FC 1
Table 3: Performance of ablation studies. Comparison of Org. (Original Baseline), MLS (Mutual Learning Scheme), MIE (Mutual
Information Estimation), and McML (Multi-column Mutual Learning) on four crowd counting datasets.
UCSD [65]WorldExpo'1o [8]
 Method
 MAE
MSE
 MAE
MSE
MAE
 MSE
 MAE
MSE
MAE
MCNN [69]
110.2
173.2
26.4
41.3
377.6
509.1
1.07
1.35
11.6
105.2
22.2
34.2
332.8
1.35
MCNN+MLS
160.3
425.3
1.04
10.8
MCNN+MIE
106.7
160.5
25.4
35.6
338.6
447.4
1.12
1.47
11.0
101.5
19.8
MCNN+McML
157.7
33.9
311.0
402.4
1.03
1.24
10.2
CSRNet [30]
68.2
115.0
16.0
266.1
397.5
10.6
1.16
1.47
8.6
CSRNet+MLS
64.2
109.3
9.9
12.3
254.2
376.3
1.00
1.31
8.4
65.6
CSRNet+MIE
111.0
9.3
12.8
264.9
387.1
1.06
1.40
8.3
CSRNet+McML
59.1
104.3
8.1
10.6
246.1
367.7
1.01
1.27
8.0
ic-CNN [44]
68.5
116.2
10.7
16.0
260.9
365.5
1.14
1.43
10.3
ic-CNN+MLS
67.4
112.8
10.3
14.6
248.4
364.3
1.02
1.28
9.7
ic-CNN+MIE
66.3
111.8
11.3
15.1
255.3
368.2
1.06
1.34
9.8
ic-CNN+McML
63.8
110.5
10.1
13.9
242.9
357.0
1.00
1.20
8.5
Finally, two fully connected layers are employed as a classifier. Sim
fine-tuned from the pre-trained VGG-16 [54]. The other layers are
ilar to [2], Leaky-ReLU [37] is used as the activation function for all
initiated in the same way as MCNN. We use Stochastic gradient
convolutional layers, and no activation function for other layers.
descent (SGD) with a fixed learning rate of 1e-6 to finetune four
Specifically, MCNN adopts 3 column structures. Each column
contains 4 convolutional layers. Intuitively, the statistical network
High-resolution column are neglected. The SGD with the learning
of MCNN uses 4 convolutional layers to embed the features as
rate of 1e-4 is used to train two columns. The learning settings of
Figure 3. CSRNet is a single column network. The first 10 convolu.
the statistical network for all baselines are the same. The number
tional layers are from pre-trained VGG-16 [54]. The last 6 dilated
of samples b is 75. Moving average is used to evaluate gradient bias.
convolutional layers are utilized to estimate the crowd counts. The
Adam optimizer with a learning rate of 1e - 4 is used to optimize
original version has 4 configurations for 6 dilated convolutional
the statistical network. More details of ground truth generation and
layers (i.e., different dilation rates). Here we treat 4 configurations
data augmentation are illustrated in supplement materials.
as 4 different columns. Similarly, as shown in Table 2, the statistical
Evaluation Details. Following previous works [30, 44, 69], we
network of CsRNet utilizes 6 convolutional layers to embed the
use mean absolute error (MAE) and mean square error (MSE) to
features for 6 dilated convolutional layers in each column. ic-CNN
evaluate the performance:
contains two columns (i.e., Low Resolution (LR) and High Reso-
|zi-z9| MSE=
(zi-z9)
lution (HR) columns). LR contains 11 convolutional layers and 2
MAE =
9
max-pooling layers, and HR has 10 convolutional layers with 2
max-pooling layers and 2 deconvolutional layers. As Table 2 shows,
where Zi is the estimated crowd count and Z9t is the ground truth
the statistical network of ic-CNN uses 5 convolutional layers to
count of the i-th image. N is the number of test images. The MAE
embed features from corresponding 5 convolutional layers after the
indicates the accuracy of the estimation, while the MSE indicates
second max pooling layer at both columns..
the robustness.
4.2 Ablation Studies
4EXPERIMENT
We have conduct extensive ablation studies on our McML.
4.1 Experiment Settings
MIE vs. MLS. We separately investigate the roles of our proposed
Datasets. To evaluate the effectiveness of our McML, we con
two improvements, i.e., Mutual Learning Scheme (MLS) and Mutual
duct experiments on four crowd counting datasets, i.e., Shang-
Information Estimation (MIE). Experimental results are shown in
haiTech [69], UCF_CC_50 [24], UCSD [8], and WorldExpo'10 [65]
Table 3. Org. is the original baseline, MLS means that we ignore the
Specifically, ShanghaiTech dataset consists of two parts: Part_A
mutual information estimation (i.e., I ) in Eqns. 3 and 4, and MIE
and Part_B. Part_A is collected from the internet and usually has
indicates that we optimize all columns at the same time (i.e., do
very high crowd density. Part_B is from busy streets and has a rela-
not alternately optimize each column). Generally speaking, MLS
tively sparse crowd density. UCF_CC_50 is mainly collected from
achieves better performance than all original baselines. After inte-
Flickr and contains images of extremely dense crowds. UCSD and
grated MIE, there is a noticeable improvement. It fully demonstrates
WorldExpo'10 are both collected from actual surveillance cameras
the effectiveness of our method..
and have low resolution and sparse crowd density. More details of
Statistical Network. We intend to compare different statistical
datasets split are illustrated in supplementary material.
networks. We have modified the proposed statistical network as fol-
Learning Settings. We use our McML to improve MCNN, CSRNet
lows: 1) Only-1-Conv means only keep the last convolutional layer.
and ic-CNN. For MCNN, the network is initiated by a Gaussian
2) Last-3-Conv denotes to preserve the last three convolutional lay-
distribution with a mean of 0 and a standard deviation of 0.01.
ers. 3) First-3-Conv indicates to retain the first three convolutional
Adam optimizer [27] with a learning rate of 1e-5 is used to train
 layers. 4) FC-3 (64) means to add one fully connected (FC) layer
three columns. For CsRNet, the first 10 convolutional layers are
with 64 outputs between the original two FC layers. 5) FC-1 (64)
Table 4: Comparison with state-of-the-art methods on ShanghaiTech [69], UCF_CC_50 [24] and UcsD [65] datasets.
ShanghaiTech A [69]
ShanghaiTech B [69]
UCF_CC_50 [24]
UCSD [65]
MSE
 MAE
 Method
Venue & Year
MAE
MSE
 MAE
MSE
 MAE
MSE
Idrees et al. [24]
CVPR
2013
419.5
541.6
Zhang et al. [65]
CVPR
2015
181.8
277.7
32.0
49.8
467.0
498.5
1.60
3.31
CCNN [39]
ECCV
2016
1.51
ECCV
2016
333.7
Hydra-2s [39]
425.3
-
-
AVSS
20.0
31.1
C-MTL [55]
2017
101.3
152.4
322.8
397.9
CVPR
90.4
135.0
21.6
33.4
318.1
SwitchCNN [50]
2017
439.2
1.62
2.10
CP-CNN [56]
ICCV
2017
73.6
106.4
20.1
30.1
295.8
320.9
Huang at al. [23]
TIP
2018
20.2
35.6
409.5
563.7
1.00
1.40
SaCNN [66]
WACV
2018
86.8
139.2
16.2
25.8
314.9
424.8
ACSCP [51]
CVPR
2018
75.7
102.7
17.2
27.4
291.0
404.6
CVPR
2018
72.5
13.6
21.1
IG-CNN [49]
118.2
291.4
349.4
Deep-NCL [53]
CVPR
2018
73.5
112.3
18.7
26.0
288.4
404.7
 MCNN [69]
CVPR
2016
110.2
173.2
26.4
41.3
377.6
509.1
1.07
1.35
CSRNet [30]
CVPR
2018
68.2
115.0
10.6
16.0
266.1
397.5
1.16
1.47
ic-CNN [44]
ECCV
2018
68.5
116.2
10.7
16.0
260.9
365.5
1.14
1.43
 MCNN+McML
101.5
157.7
19.8
33.9
311.0
402.4
1.03
1.24
CSRNet+McML
59.1
104.3
8.1
10.6
246.1
367.7
1.01
1.27
ic-CNN+McML
63.8
110.5
10.1
13.9
242.9
357.0
1.00
1.20
Table 6: Ablation studies of statistical networks on ShanghaiTech
indicates to reduce the outputs of the first FC layer into 64. 6) FC-1
Part A dataset [69].
(256) states to increase the outputs of the first FC layer into 256
Comparison results are illustrated in Table 6. In general, different
MCNN [69]
CSRNet [30]
ic-CNN [44]
statistical networks have no significant difference in performance
Structures
MAE MSE
MAEMSE
MAE MSE
Even using only one convolutional layer, our proposed training
 Only-1-Conv
104.2
160.8
61.7
106.9
66.2
114.1
strategy still obviously improve the original baseline. These results
Last-3-Conv
103.5
160.1
61.1
106.8
65.5
113.3
 First-3-Conv
103.2
159.7
60.7
106.1
64.8
113.2
fully demonstrate the robustness of our method.
FC-3 (64)
101.6
157.8
59.3
104.3
63.9
110.5
The number of samples b. We study the effect of the number of.
 FC-1 (64)
102.0
158.2
59.8
105.1
64.5
111.3
samples b. As shown in Figure 4, we obverse that with the number
FC-1 (256)
102.2
158.4
104.8
63.9
111.0
59.7
of b increases, the performance first increases and then decreases.
157.7
Ours (Table 2)
101.5
59.1
104.3
63.8
110.5
Typically, when b is too small, because of the estimated mutual
information has a severe bias, our method intuitively gets poor
4.3
Comparisons with State-of-the-art
performance. In contrast, when b is too large, although the mutual
We demonstrate the efficiency of our McML on four challenging
information has been accurately estimated, the performance of our
crowd counting datasets. Tables 4 and 7 show the comparison with
model is still severely affected since the iterations of the mutual
the other state-of-the-art methods. We observe that McML can
learning scheme are inadequate. Based on that we use a binary
significantly improve three baselines (i.e., MCNN, CSRNet, and
search to find the best value of b. After extensive cross-validation,
ic-CNN) on all datasets. Notably, after using McML, the optimized.
b is set to 75 for all baselines.
CSRNet and ic-CNN also obviously outperform the other state-
The weight of a. We have verified the impact of the weight of a.
of-the-art approaches. It fully demonstrates that our method can
To get a more accurate setting, we perform a grid search with the
not only be applied to any multi-column network but also works
step of 0.1. The best values of a for different datasets are illustated
on both dense and sparse crowd scenes. Additionally, although
in Table 5. Since ShanghaiTech Part A and UCF_CC_50 have more
 ic-CNN also propose an alternate training process, our McML can
substantial scale changes, they have a larger a than other datasets.
still achieve better results than the original ic-CNN. It means that
We assume that the weight of a positively correlates to the degree
our McML is more effective than ic-CNN.
of scale changes.
For ShanghaiTech dataset, McML significantly boosts MCNN,
Datasets
CSRNet, and ic-CNN with relative MAE improvements of 7.9%,
1%
0.3
13.3% and 6.9% on Part A, and 25.0%, 23.6% and 5.6% on Part B,
ShanghaiTech A
respectively. Similarly, for UCF CC 50 dataset, McML provides the
 ShanghaiTech B
0.2
relative MAE improvements of 17.6%, 7.5%, and 6.9% for three base-
UCF_CC_50
0.4
lines. These results clearly state McML can not only handle dense
0.1
UCSD
crowd scenes but also work for small datasets. On the other hand,
The Number of Samples b
WorldExpo'10
0.2
experimental results of UCSD dataset show McML can improve the
accuracy (i.e., lower MAE) and gain the robustness (i.e., lower MSE).
Figure 4: Effects of samples b.
Table 5: The values of a.
This result states the effectiveness of McML on the sparse-crowd
scene. Additionally, on WorldExpo'10 dataset, although our pro-
posed McML does not utilize perspective maps, they still achieve
MCNN-
Figure 5: Comparison of estimated density maps between MCNN [69] and McML. +' indicates employing McML on the original MCNN.
Table 7: Comparison with state-of-the-art methods on World-
Table 8: The result analysis of our proposed McML. The values in
Expo'1o [8] dataset. Only MAE is computed for each scene and then
the table are the average of all columns. Col.>Col. is the result be-
averaged to evaluate the overall performance.
tween different columns. Col.< >GT is the result between the ensem-
ble of all columns and the ground truth.
 Method
S1
S2
S3
S4
S5
Avg.
Zhang et al. [65]
9.8
14.3
22.2
3.7
12.9
Co
14.1
Col.> GT
Huang et al. [23]
21.7
11.9
11.0
3.5
10.5
 Method
4.1
 MIC
SSIM
MIC
SSIM
Switch-CNN [50]
15.7
10.0
11.0
5.9
4.4
9.4
ShanghaiTech Part A [69]
SaCNN [66]
2.6
[3.5
10.6
12.5
3.3
8.5
MCNN+McML
0.74
0.61
0.68
0.70
CP-CNN [56]
10.4
8.9
2.9
14.7
10.5
5.8
CSRNet+McML
0.77
0.70
0.82
0.82
MCNN [69]
3.4
20.6
12.9
13.0
8.1
11.6
ic-CNN+McML
0.76
0.55
0.80
0.76
CSRNet [30]
2.9
11.5
8.6
16.6
3.4
8.6
JCF
_50 [24]
12.3
ic-CNN [44]
17.0
9.2
8.1
4.7
10.3
MCNN+McML
0.69
0.48
0.79
0.47
MCNN+McML
3.4
15.2
14.6
12.7
5.2
10.2
CSRNet+McML
0.73
0.60
0.75
0.61
CSRNet+McML
2.8
11.2
9.0
13.5
8.0
ic-CNN+McML
0.75
0.60
0.72
0.64
ic-CNN+McML
10.7
11.2
8.2
8.0
4.5
8.5
CONCLUSION
5
better results than other state-of-the-art methods that use perspec-
In this paper, we propose a novel learning strategy called Multi-
tive maps.
column Mutual learning (McML) for crowd counting, which can
improve the scale invariance of feature learning and reduce pa-
4.4Why does McML Work
rameter redundancy to avoid overfitting. It could be applied to all
We attempt to give more insights to show why our McML works.
existing CNN-based multi-column networks and is end-to-end train-
The statistical analysis is illustrated in Table 8. Compared with
able. Experiments on four challenging datasets fully demonstrate
the results without McML (in Table 1), we observe that McML can
that it can significantly improve all baselines and outperforms the
significantly reduce Maximal Information Coefficient (MIC) and
other state-of-the-art methods. In summary, this work provides the
Structural SIMilarity (SsiM) between columns. It denotes that our
elegant views of effectively using multi-column architectures to
method can indeed reduce the redundant parameters of columns
improve the scale invariance. In future work, we will study how to
and avoid overfitting. On the other hand, McML can efficiently
handle different image scales and resolutions in the ground truth
improve MIC and SSIM between the ensemble of all columns and
generation.
the ground truth. It means that our method can guide multi-column
structures to learn different scale features and improve the accuracy
6ACKNOWLEDGEMENTS
of crowd counting.
This research was supported in part through the financial assistance award
To further verify that our McML can indeed guide multi-column
60NANB17D156 from U.S. Department of Commerce, National Institute
networks to learn different scales, we showcase the generated den-
of Standards and Technology and by the Intelligence Advanced Research
sity maps from different columns of MCNN in Figure 5. These four
examples typically contain different crowd densities, occlusions,
Center (DOI/IBC) contract number D17PC00340, National Natural Science
and scale changes. We observe that estimated density maps of
Foundation of China (Grant No: 61772436), Foundation for Department
McML have more different salient areas than the original MCNN. It
of Transportation of Henan Province, China (2019J-2-2), Sichuan Science
 means that our method can indeed guide multi-column structures
and Technology Innovation Seedling Fund (2017RZo015), China Scholar-
to focus on different scale information (i.e., different people/head
ship Council (Grant No. 201707000083) and Cultivation Program for the
sizes). It is noted that the ground truth itself is generated with center
Excellent Doctoral Dissertation of Southwest Jiaotong University (Grant.
points of pedestrians' heads, which inherently contains inaccurate
No. D-YB 201707).
information. Thus the result of our method is still unable to produce
the same density map to the ground truth.
REFERENCES
IEEE transactions on pattern analysis and machine intelligence 37, 10 (2015), 1986
[1] Jimmy Ba and Rich Caruana. 2014. Do deep nets really need to be deep? In
1998.
Advances in neural information processing systems. 2654-2662.
[26] Di Kang and Antoni B. Chan. 2018. Crowd Counting by Adaptively Fusing
Predictions from an Image Pyramid. In Proceedings of British Machine Vision
[2] Mohamed Ishmael Belghazi, Aristide Baratin, Sai Rajeswar, Sherjil Ozair, Yoshua
Conference. 89.
Bengio, Aaron Courville, and R Devon Hjelm. 2018. Mine: mutual information
[27] Diederik P Kingma and Jimmy Ba. 2014. Adam: A method for stochastic opti-
neural estimation. arXiv preprint arXiv:1801.04062 (2018).
mization. arXiv preprint arXiv:1412.6980 (2014).
[3] Lokesh Boominathan, Srinivas S. S. Kruthiventi, and R. Venkatesh Babu. 2016.
CrowdNet: A Deep Convolutional Network for Dense Crowd Counting. In Pro-
ceedings of ACM International Conference on Multimedia. 640-644.
information based on Parzen window. IEEE Transactions on Pattern Analysis &
Machine Intelligence 12 (2002), 1667-1671.
[4] Gabriel J Brostow and Roberto Cipolla. 2006. Unsupervised bayesian detection of
independent motion in crowds. In Proceedings of the IEEE conference on computer
Images. In Proceedings of Conference on Neural Information Processing Systems.
vision and pattern recognition, Vol. 1. 594-601.
1324-1332.
[5] Gavin Brown, Jeremy L Wyatt, and Peter Tino. 2005. Managing diversity in
[30] Yuhong Li, Xiaofan Zhang, and Deming Chen. 2018. CsRNet: Dilated Con-
regression ensembles. Journal of Machine Learning Research 6, Sep (2005), 1621-
volutional Neural Networks for Understanding the Highly Congested Scenes.
1650.
In Proceedings of IEEE Conference on Computer Vision and Pattern Recognition.
[6] Atul J Butte and Isaac S Kohane. 1999. Mutual information relevance networks:
functional genomic clustering using pairwise entropy measurements. In Biocom.
1091-1100.
[31] Sheng-Fuu Lin, Jaw-Yeh Chen, and Hung-Xin Chao. 2001. Estimation of number
puting. 418-429.
 of people in crowded scenes using perspective transformation. IEEE Transactions
[7] Xinkun Cao, Zhipeng Wang, Yanyun Zhao, and Fei Su. 2018. Scale Aggregation
Network for Accurate and Efficient Crowd Counting. In Proceedings of European
on Systems, Man, and Cybernetics-Part A: Systems and Humans 31, 6 (2001), 645-
Conference on Computer Vision. 757-773.
654.
[32] Jiang Liu, Chenqiang Gao, Deyu Meng, and Alexander G. Hauptmann. 2018. Deci
[8] Antoni B Chan, Zhang-Sheng John Liang, and Nuno Vasconcelos. 2o08. Pri-
 deNet: Counting Varying Density Crowds Through Attention Guided Detection
vacy preserving crowd monitoring: Counting people without people models or
and Density Estimation. In Proceedings of IEEE Conference on Computer Vision
tracking. In Proceedings of the IEEE conference on computer vision and pattern
recognition. 1-7.
[33] Ning Liu, Yongchao Long, Changqing Zou, Qun Niu, Li Pan, and Hefeng Wu.
[9] Antoni B Chan and Nuno Vasconcelos. 2012. Counting people with low-level
features and Bayesian regression. IEEE Transactions on Image Processing 21, 4
2018. ADCrowdNet: An Attention-injective Deformable Convolutional Network
for Crowd Understanding. CoRR abs/1811.11968 (2018).
(2012), 2160-2177.
[34] Weizhe Liu, Krzysztof Lis, Mathieu Salzmann, and Pascal Fua. 2018. Geometric
[10] Ke Chen, Shaogang Gong, Tao Xiang, and Chen Change Loy. 2013. Cumulative
and Physical Constraints for Head Plane Crowd Density Estimation in Videos.
CoRR abs/1803.08805 (2018).
conference on computer vision and pattern recognition. 2467-2474.
[11] Ke Chen, Chen Change Loy, Shaogang Gong, and Tony Xiang. 2012. Feature
[35] Weizhe Liu, Mathieu Salzmann, and Pascal Fua. 2018. Context-Aware Crowd
Mining for Localised Crowd Counting. In Proceedings of British Machine Vision
Counting. CoRR abs/1811.10452 (2018).
[36] Zheng Ma and Antoni B. Chan. 2013. Crossing the Line: Crowd Counting by
Conference. 1-11.
Integer Programming with Local Features. In Proceedings of IEEE Conference on
[12] Zhi-Qi Cheng, Jun-Xiu Li, Qi Dai, Xiao Wu, and Alexander Hauptmann. 2019.
Learning Spatial Awareness to Improve Crowd Counting. In Proceedings of IEEE
Computer Vision and Pattern Recognition. 2539-2546.
[37] Andrew L Maas, Awni Y Hannun, and Andrew Y Ng. 2013. Rectifier nonlinearities
International Conference on Computer Vision.
[13] Zhi-Qi Cheng, Xiao Wu, Siyu Huang, Jun-Xiu Li, Alexander G. Hauptmann, and
improve neural network acoustic models. In ICML Workshop on Deep Learning
for Audio, Speech and Language Processing.
Qiang Peng. 2018. Learning to Transfer: Generalizable Attribute Learning with
Multitask Neural Model Search. In Proceedings of the 26th ACM International
 [38] Frederik Maes, Andre Collignon, Dirk Vandermeulen, Guy Marchal, and Paul
Suetens. 1997. Multimodality image registration by maximization of mutual
Conference on Multimedia.
information. IEEE transactions on Medical Imaging 16, 2 (1997), 187-198.
[14] Zhi-Qi Cheng, Xiao Wu, Yang Liu, and Xian-Sheng Hua. 2017. Video2shop: Exact
[39] Daniel Onoro-Rubio and Roberto Javier Lopez-Sastre. 2016. Towards Perspective-
matching clothes in videos to online shopping images. In Proceedings of the IEEE
Free Object Counting with Deep Learning. In Proceedings of European Conference
Conference on Computer Vision and Pattern Recognition. 4048-4056..
on Computer Vision. 615-629.
[15] Zhi-Qi Cheng, Hao Zhang, Xiao Wu, and Chong-Wah Ngo. 2017. On the selection
[40] Liam Paninski. 2003. Estimation of entropy and mutual information. Neural
of anchors and targets for video hyperlinking. In Proceedings of the 2017 ACM on
computation 15, 6 (2003), 1191-1253.
International Conference on Multimedia Retrieval. 287-293.
[41] Nikos Paragios and Visvanathan Ramesh. 2001. A MRF-based approach for real-
[16] Navneet Dalal and Bill Triggs. 2005. Histograms of oriented gradients for human
time subway monitoring. In Proceedings of the IEEE conference on computer vision
detection. In Proceedings of the IEEE conference on computer vision and pattern
and pattern recognition, Vol. 1. I-I.
recognition, Vol. 1. 886-893.
[17] Piotr Dollar, Boris Babenko, Serge Belongie, Pietro Perona, and Zhuowen Tu. 2008.
Multiple component learning for object detection. In Proceedings of European
 on mutual information: criteria of max-dependency, max-relevance, and min-
redundancy. IEEE Transactions on Pattern Analysis & Machine Intelligence 8 (2005),
Conference on Computer Vision. 211-224.
1226-1238.
[18] Monroe D Donsker and SR Srinivasa Varadhan. 1983. Asymptotic evaluation of
[43] Viet-Quoc Pham, Tatsuo Kozakaya, Osamu Yamaguchi, and Ryuzo Okada. 2015.
COUNT Forest: CO-Voting Uncertain Number of Targets Using Random Forest
and Applied Mathematics 36, 2 (1983), 183-212
for Crowd Density Estimation. In Proceedings of International Conference on
[19] Manuel Fernandez-Delgado, Eva Cernadas, Senen Barro, and Dinani Amorim
Computer Vision. 3253-3261.
2014. Do we need hundreds of classifiers to solve real world classification
problems? The Fournal of Machine Learning Research 15, 1 (2014), 3133-3181.
[44] Viresh Ranjan, Hieu Le, and Minh Hoai. 2018. Iterative Crowd Counting. In
 Proceedings of European Conference on Computer Vision. 278-293.
[20] R Devon Hjelm, Alex Fedorov, Samuel Lavoie-Marchildon, Karan Grewal, Adam
[45] Carlo S Regazzoni and Alessandra Tesei. 1996. Distributed data fusion for real
Trischler, and Yoshua Bengio. 2018. Learning deep representations by mutual
time crowding estimation. Signal Processing 53, 1 (1996), 47-63.
information estimation and maximization. arXiv preprint arXiv:1808.06670 (2018).
[46] Ye Ren, Le Zhang, and Ponnuthurai N Suganthan. 2016. Ensemble classification
[21] Siyu Huang, Xi Li, Zhiqi Cheng, Zhongfei Zhang, and Alexander G. Hauptmann
and regression-recent developments, applications and future directions. IEEE
2018. Stacked Pooling: Improving Crowd Counting by Boosting Scale Invariance.
Computational intelligence magazine 11, 1 (2016), 41-53
CoRR abs/1808.07456 (2018).
[47] David Ryan, Simon Denman, Clinton Fookes, and Sridha Sridharan. 2009. Crowd
[22] Siyu Huang, Xi Li, Zhi-Qi Cheng, Zhongfei Zhang, and Alexander Hauptmann.
counting using multiple local features. In Digital Image Computing: Techniques
2018. GNAS: A Greedy Neural Architecture Search Method for Multi-Attribute
and Applications. 81-88.
Learning. In 2018 ACM Multimedia Conference on Multimedia Conference. ACM,
[48] Deepak Babu Sam and R. Venkatesh Babu. 2018. Top-Down Feedback for Crowd
2049-2057.
Counting Convolutional Neural Network. In Proceedings of Conference on Artificial
[23] Siyu Huang, Xi Li, Zhongfei Zhang, Fei Wu, Shenghua Gao, Rongrong Ji, and
Intelligence. 7323-7330.
Junwei Han. 2018. Body Structure Aware Deep Crowd Counting. IEEE Trans.
[49] Deepak Babu Sam, Neeraj N. Sajjan, R. Venkatesh Babu, and Mukundhan Srini
Image Processing 27, 3 (2018), 1049-1059.
vasan. 2018. Divide and Grow: Capturing Huge Diversity in Crowd Images With
source Multi-scale Counting in Extremely Dense Crowd Images. In Proceedingse
Incrementally Growing CNN. In Proceedings of IEEE Conference on Computer
Vision and Pattern Recognition. 3618-3626.
of IEEE Conference on Computer Vision and Pattern Recognition. 2547-2554.
[25] Haroon Idrees, Khurram Soomro, and Mubarak Shah. 2015. Detecting humans in
tional Neural Network for Crowd Counting. In Proceedings of IEEE Conference on
dense crowds using locally-consistent scale prior and global occlusion reasoning
Computer Vision and Pattern Recognition. 4031-4039.
[51] Zan Shen, Yi Xu, Bingbing Ni, Minsi Wang, Jianguo Hu, and Xiaokang Yang. 2018.
on computer vision and pattern recognition. 3401-3408.
Crowd Counting via Adversarial Cross-Scale Consistency Pursuit. In Proceedings
[62] Ze Wang, Zehao Xiao, Kai Xie, Qiang Qiu, Xiantong Zhen, and Xianbin Cao. 2018.
of IEEE Conference on Computer Vision and Pattern Recognition. 5245-5254.
In Defense of Single-column Networks for Crowd Counting. In Proceedings of
 [52] Miaojing Shi, Zhaohui Yang, Chao Xu, and Qijun Chen. 2018. Perspective-Aware
British Machine Vision Conference. 78.
CNN For Crowd Counting. CoRR abs/1807.01989 (2018).
[63] Xingjiao Wu, Yingbin Zheng, Hao Ye, Wenxin Hu, Jing Yang, and Liang He. 2018.
[53] Zenglin Shi, Le Zhang, Yun Liu, Xiaofeng Cao, Yangdong Ye, Ming-Ming Cheng,
Adaptive Scenario Discovery for Crowd Counting. CoRR abs/1812.02393 (2018).
 and Guoyan Zheng. 2018. Crowd Counting With Deep Negative Correlation
[64] Lingke Zeng, Xiangmin Xu, Bolun Cai, Suo Qiu, and Tong Zhang. 2017. Multi-
Learning. In Proceedings of IEEE Conference on Computer Vision and Pattern
scale convolutional neural networks for crowd counting. In Proceedings of Inter-
Recognition. 5382-5390.
national Conference on Image Processing. 465-469.
[54] Karen Simonyan and Andrew Zisserman. 2014. Very deep convolutional networks
[65] Cong Zhang, Hongsheng Li, Xiaogang Wang, and Xiaokang Yang. 2015. Cross-
for large-scale image recognition. arXiv preprint arXiv:1409.1556 (2014).
scene crowd counting via deep convolutional neural networks. In Proceedings of
[55] Vishwanath A. Sindagi and Vishal M. Patel. 2017. CNN-Based cascaded multi-
IEEE Conference on Computer Vision and Pattern Recognition. 833-841.
task learning of high-level prior and density estimation for crowd counting.
[66] Lu Zhang, Miaojing Shi, and Qiaobo Chen. 2018. Crowd Counting via Scale.
In Proceedings of International Conference on Advanced Video and Signal Based
 Adaptive Convolutional Neural Network. In Proceedings of Winter Conference on
Surveillance. 1-6.
Applications of Computer Vision. 1113-1121.
[56] Vishwanath A. Sindagi and Vishal M. Patel. 2017. Generating High-Quality Crowd
[67] Le Zhang and Ponnuthurai Nagaratnam Suganthan. 2017. Benchmarking ensem-
Density Maps Using Contextual Pyramid CNNs. In Proceedings of International
 ble classifiers with novel co-trained kernel ridge regression and random vector
Conference on Computer Vision. 1879-1888.
functional link ensembles [research frontier]. IEEE Computational Intelligence
[57] Yukun Tian, Yimei Lei, Junping Zhang, and James Z. Wang. 2018. PaDNet:
Magazine 12, 4 (2017), 61-72.
Pan-Density Crowd Counting. CoRR abs/1811.02805 (2018).
[68] Youmei Zhang, Chunluan Zhou, Faliang Chang, and Alex C. Kot. 2018. Attention
[58] Paul Viola and Michael Jones. 2001. Rapid object detection using a boosted
to Head Locations for Crowd Counting. CoRR abs/1806.10287 (2018).
[69] Yingying Zhang, Desen Zhou, Siqin Chen, Shenghua Gao, and Yi Ma. 2016.
cascade of simple features. In Proceedings of the IEEE conference on computer
vision and pattern recognition, Vol. 1. I-I.
Single-Image Crowd Counting via Multi-Column Convolutional Neural Network.
[59] Paul Viola, Michael J Jones, and Daniel Snow. 2005. Detecting pedestrians using
In Proceedings of IEEE Conference on Computer Vision and Pattern Recognition.
589-597.
patterns of motion and appearance. International Fournal of Computer Vision 63,
2 (2005), 153-161.
[70] Tao Zhao, Ram Nevatia, and Bo Wu. 2008. Segmentation and tracking of multiple
[60] Elad Walach and Lior Wolf. 2016. Learning to Count with CNN Boosting. In
humans in crowded environments. IEEE transactions on pattern analysis and
 Proceedings of European Conference on Computer Vision. 660-676.
 machine intelligence 30, 7 (2008), 1198-1211.
[61] Meng Wang and Xiaogang Wang. 2011. Automatic adaptation of a generic
 pedestrian detector to a specific traffic scene. In Proceedings of the IEEE conference
