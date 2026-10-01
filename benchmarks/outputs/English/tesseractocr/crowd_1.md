1909.07608v1 [cs.CV] 17 Sep 2019

arXiv

Improving the Learning of Multi-column Convolutional Neural
Network for Crowd Counting

Zhi-Qi Cheng!**, Jun-Xiu Li! **, Qi Dai?, Xiao Wu", Jun-Yan He!, Alexander G. Hauptmann?
Southwest Jiaotong University, Carnegie Mellon University, *Microsoft Research
{zhiqic,alex}@cs.cmu.edu, {lijunxiu@my, wuxiaohk @home}.swjtu.edu.cn, gid@microsoft.com, junyanhe1989@gmail.com

ABSTRACT

Tremendous variation in the scale of people/head size is a critical
problem for crowd counting. To improve the scale invariance of
feature representation, recent works extensively employ Convo-
lutional Neural Networks with multi-column structures to handle
different scales and resolutions. However, due to the substantial re-
dundant parameters in columns, existing multi-column networks in-
variably exhibit almost the same scale features in different columns,
which severely affects counting accuracy and leads to overfitting.
In this paper, we attack this problem by proposing a novel Multi-
column Mutual Learning (McML) strategy. It has two main innova-
tions: 1) A statistical network is incorporated into the multi-column
framework to estimate the mutual information between columns,
which can approximately indicate the scale correlation between
features from different columns. By minimizing the mutual infor-
mation, each column is guided to learn features with different
image scales. 2) We devise a mutual learning scheme that can al-
ternately optimize each column while keeping the other columns
fixed on each mini-batch training data. With such asynchronous
parameter update process, each column is inclined to learn different
feature representation from others, which can efficiently reduce the
parameter redundancy and improve generalization ability. More
remarkably, McML can be applied to all existing multi-column
networks and is end-to-end trainable. Extensive experiments on
four challenging benchmarks show that McML can significantly
improve the original multi-column networks and outperform the
other state-of-the-art approaches.

KEYWORDS
Crowd Counting; Multi-column Network; Mutual Learning Strategy

ACM Reference Format:

Zhi-Qi Cheng, Jun-Xiu Li, Qi Dai, Xiao Wu, Jun-Yan He, Alexander G. Haupt-
mann. 2019. Improving the Learning of Multi-column Convolutional Neural
Network for Crowd Counting. In Proceedings of the 27th ACM International
Conference on Multimedia (MM ’19), Oct. 21-25, 2019, Nice, France. ACM,
New York, NY, USA, 11 pages. https://doi.org/10.1145/3343031.3350898

 

*Equal contribution. This work was done when Zhi-Qi Cheng and Jun-Xiu Li visited
at Microsoft Research. Xiao Wu is the corresponding author.

Permission to make digital or hard copies of all or part of this work for personal or
classroom use is granted without fee provided that copies are not made or distributed
for profit or commercial advantage and that copies bear this notice and the full citation
on the first page. Copyrights for components of this work owned by others than ACM
must be honored. Abstracting with credit is permitted. To copy otherwise, or republish,
to post on servers or to redistribute to lists, requires prior specific permission and/or a
fee. Request permissions from permissions@acm.org.

MM ’19, October 21-25, 2019, Nice, France

© 2019 Association for Computing Machinery.

ACM ISBN 978-1-4503-6889-6/19/10...$15.00
https://doi.org/10.1145/3343031.3350898

 

Figure 1: Examples of ShanghaiTech Part A dataset [69]. Crowd
counting is a challenging task with the significant variation in the
people/head size due to the perspective effect.

1 INTRODUCTION

With the growth of wide applications, such as safety monitoring,
disaster management, and public space design, crowd counting has
been extensively studied in the past decade. As shown in Figure 1, a
significant challenge of crowd counting lies in the extreme variation
in the scale of people/head size. To improve the scale invariance
of feature learning, Multi-column Convolutional Neural Networks
are extensively studied [3, 12, 21, 32, 44, 50, 69]. As illustrated in
Figure 2, the motivation of multi-column networks is intuitive. Each
column is devised with different receptive fields (e.g., different filter
sizes) so that the features learned by different columns are expected
to focus on different scales and resolutions. By assembling features
from all columns, multi-column networks are easily adaptive to the
large variations of the scale due to the generalization ability across
scales and resolutions.

Although multi-column architecture is naturally employed for
addressing the issue of various scale change, previous works [12,
21, 30, 44, 62] have pointed out that different columns always gen-
erate features with almost the same scale, which indicates that
existing multi-column architectures cannot effectively improve the
scale invariance of feature learning. To further verify this observa-
tion, we have extensively analyzed three state-of-the-art networks,
i.e., MCNN [69], CSRNet [30] and ic-CNN [44]. It is worth noting
that CSRNet is a single column network, which has four different
configurations (i.e., different dilation rates). We remould CSRNet
to treat each configuration as a column, and design a four-column
network as an alternative. The Maximal Information Coefficient
(MIC)! and the Structural SIMilarity (SSIM)? are computed based on
the results of different columns. MIC measures the strength of asso-
ciation between the outputs (i.e., crowd counts) and SSIM measures
the similarity between density maps. As shown in Table 1, different
columns (Col.~Col.) always output almost the same counts (i.e.,
high MIC) and the similar estimated density maps (i.e., high SSIM).
In contrast, a large gap between the ensemble of all columns and
the ground truth (Col.<>GT.) still exists. This comparison shows

Thttps://en.wikipedia.org/wiki/Maximal_information_coefficient
“https://en.wikipedia.org/wiki/Structural_similarity

Table 1: The result analysis of three multi-column networks. The
values in the table are the average of all columns. Col.<Col. is the
result between different columns. Col.GT is the result between
the ensemble of all columns and the ground truth.

Col.© Col. Col.~ GT
Method MIC | SSIM | MIC | SSIM

ShanghaiTech Part A [69]
MCNN [69] 0.94 0.71 0.52 0.55
CSRNet [30] 0.93 0.84 0.74 0.71
ic-CNN [44] 0.92 0.72 0.70 0.68
UCF_CC_50 [24]
MCNN [69] 0.81 0.53 0.70 0.36
CSRNet [30] 0.87 0.72 0.71 0.48
ic-CNN [44] 0.93 0.70 0.57 0.52

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

that there are substantial redundant parameters among columns,
which makes multi-column architecture fails to learn the features
across different scales. On the other hand, it indicates that existing
multi-column networks tend to overfit the data and can not learn
the essence of the ground truth.

Inspired by previous works [30, 44, 62], we reveal that the prob-
lem of existing multi-column networks lies in the difficulty of learn-
ing features with different scales. Generally speaking, there are
two main problems: 1) There is no supervision to guide multiple
columns to learn features at different scales. The current learning
objective is only to minimize the errors of crowd count. Although
we have designed different columns to have different receptive
fields, they are still gradually forced to generate features with al-
most the same scale along with the network optimization. 2) There
are huge redundant parameters among columns. Because of parallel
column architectures, multi-column networks naturally brought in
redundant parameters. As the analysis of [1], with the increase of
parameters, a more substantial amount of training data is also re-
quired. It implies that existing multi-column networks are typically
harder to train and easier to overfit.

In this paper, we propose a novel Multi-column Mutual Learning
(McML) strategy to improve the learning of multi-column networks.
As illustrated in Figure 3, our McML addresses the above two issues
from two aspects. 1) A statistical network is proposed to measure
the mutual information between different columns. The mutual
information can approximately measure the scale correlation be-
tween features from different columns. By additionally minimizing
the mutual information in the loss, different column structures
are forced to learn feature representations with different scales.
2) Instead of the conventional optimization that updates the pa-
rameters of multiple columns simultaneously, we devise a mutual
learning scheme that can alternately optimize each column while
keeping the other columns fixed on each mini-batch training data.
With such asynchronous learning steps, each column is inclined
to learn different feature representation from others, which can
efficiently reduce the parameter redundancy and improve the gener-
alization ability. The proposed McML can be applied to all existing
multi-column networks and is end-to-end trainable. We conduct
extensive experiments on four datasets to verify the effectiveness
of our method.

The main contribution of this work is the proposal of Multi-
column Mutual Learning (McML) strategy to improve the learning
of multi-column networks. The solution also provides the elegant
views of how to explicitly supervise multi-column architectures to

learn features with different scales and how to reduce the enormous
redundant parameters and avoid overfitting, which are problems
not yet fully understood in the literature.

2 RELATED WORK
2.1 Detection-based Methods

These models use visual object detectors to locate people in images.
Given the individual localization of each people, crowd counting
becomes trivial. There are two directions in this line, i.e., detection
on 1) whole pedestrians [4, 16, 58, 70] and 2) parts of pedestrians
[17, 25, 31, 61]. Typically, local features [16, 31] are first extracted
and then are exploited to train various detectors (e.g., SVM [31]
and AdaBoost [59]). Although these works achieve satisfactory
results for the low-density scenario, they are unable to generalize
for high-density images since it is impossible to train a detector for
extremely crowded scenes.

2.2 Regression-based Methods

Different from detection-based models, regression-based methods
directly estimate crowd count using image features. It has two
steps: 1) extract powerful image features, 2) use various regression
models to estimate the crowd count. Specifically, image features
include edge features [9, 11, 36, 45, 47] and texture features [10,
11, 24, 43]. Regression methods cover Bayesian [9], Ridge [11],
Forest [43] and Markov Random Field [24, 41]. Since these works
always use handcrafted low-level features, they still cannot obtain
satisfactory performance.

2.3. CNN-based Methods

Due to substantial variations in the scale of people/head size, most
recent studies extensively use Convolutional Neural Networks
(CNN) with multi-column structures for crowd counting. Specifi-
cally, a dual-column network is proposed by [3] to merge shallow
and deep layers to estimate crowd counts. Inspired by this work,
a great three-column network named MCNN is proposed by [69],
which employs different filters on separate columns to obtain the
various scale features. Noted that there are a lot of works to con-
tinually improve MCNN [26, 55, 56, 60]. Sam et al. [50] introduce a
switching structure, which uses a classifier to assign input image
patches to best column structures. Recently, Liu et al. [32] propose
a multi-column network to simultaneously estimate crowd density
by detection and regression models. Ranjan et al. [44] employ a
two-column structure to iterative train their model with different
resolution images.

In addition to multi-column networks, there are a lot of methods
to improve scale invariance of feature learning by 1) studying on the
fusion of multi-scale features [35, 57, 62, 63], 2) studying on multi-
blob based scale aggregation networks [7, 64], 3) designing scale-
invariant convolutional or pooling layers [21, 30, 33, 56, 62], and
4) studying on automated scale adaptive networks [48, 49, 66]. On
the other hand, a lot of studies devote to using perspective maps [52],
geometric constraints [34, 68], and region-of-interest [33] to further
improve the counting accuracy.

These state-of-the-art methods aim to improve the scale invari-
ance of feature learning. Inspired by recent studies [30, 44, 62], we
reveal that existing multi-column networks cannot effectively learn
different scale features as Sec. 1. To solve this problem, we propose

( Conv7-32 conv7-1s 7
Conv9-16| Maxpool | Maxpool Conv7-8 |
|
| f
‘Conv7-20 Conv5-40 Conv5-20, Convs-10, :
Maxpool Maxpool / coma

Tee ate | Sota 1)

 

 

 

Conv5-24

Figure 2: The architecture of MCNN [69]. It is a classical Multi-
column Convolutional Neural Network. It employs different size of
filters on three columns to obtain different scale features.

a novel Multi-column Mutual Learning (McML) strategy, which can
be applied to all existing CNN-based multi-column networks and is
end-to-end trainable. It is noted that the previous work ic-CNN [44]
also proposes an iterative learning strategy to improve the learning
of multi-column networks. Different from our McML, since ic-CNN
is designed for a specific neural architecture, it can not be gener-
alized to all multi-column networks. Additionally, we have tested
our McML on the same network of ic-CNN. Experimental results
show that McML can still significantly improve the performance of
the original ic-CNN.

3 MULTI-COLUMN MUTUAL LEARNING

In this section, we present the proposed Multi-column Mutual
Learning (McML) strategy. The problem formulation is first in-
troduced in Sec. 3.1. Then the overview of our McML is described
in Sec. 3.2. More details of McML are illustrated in Sec. 3.3 to 3.5.

3.1 Problem Formulation

Recent studies define crowd counting task is as a density regression
problem [7, 29, 69]. Given N training images X = {x,--- , xy} as
the training set, each image x; is annotated with a total of c; center
points of pedestrians’ heads PY ’ = {P,,Po,---, Po, }. Typically, the
ground truth density map y; of image x; is generated as,

Vp € Xi. yi = » N9'(p; p= P,o”), (1)
Pep?’

where p is a pixel and N¥ is a Gaussian kernel with standard
deviation o. The number of people c; in image x; is equal to the
sum of density of all pixels as )) pcx, yi(p) = ci. With these training
data, crowd counting models aim to learn a regression model G
with parameters 0 to minimize the difference between estimated
density map Gg(x;) and ground truth density map Yj. Specifically,
Euclidean distance, i.e., Lz loss is employed to get an approximate
solution,

L -1S\@ (xi) - yi)? (2)
2 ON Z O\Xi Yi) »

where as the size of input images are different, the value of Eqn. 2
is further normalized by the number of pixels in each image.

It is noted that, as shown in Figure 1, enormous variation in the
scale of people/head size is a critical problem for crowd counting.
Many studies [5, 13, 19, 22, 46, 67] have proved that only using
an individual regression model is theoretically far from the global
optimal. To improve the scale invariance of feature learning, Convo-
lutional Neural Networks with multi-column structures are exten-
sively studied by recent works [26, 55, 56, 60, 69]. Figure 2 illustrates

a typical multi-column network named MCNN [69]. The intentions
of multi-column networks are natural, where each column structure
is devised with different receptive fields (e.g., different filter sizes)
so that the features learned by individual column is expected to
focus on a particular scale of people/head size. With the ensemble
of features from all columns, multi-column networks are easily
adaptive to handle the large scale variations.

Although the motivation for multi-column structures is straight-
forward, previous works [30, 44, 62] have pointed out that existing
multi-column networks cannot improve the scale invariance of
features learning. As analyzed in Sec. 1, we are convinced that
there are abundant redundant parameters between columns, which
causes multi-column structures to fail to learn the features across
different scales and invariably get almost the same estimated crowd
counts and density maps. After thoroughly surveying previous
works [30, 44, 46, 62, 67] and analyzing our experimental results in
Table 1, we further reveal that the main problem of existing multi-
column networks lies in the learning process. Generally speaking,
current learning strategy has two main weaknesses. 1) It only opti-
mizes the objective of crowd counting, while completely ignores
the intention of using multi-column structures to learn different
scale features. 2) It instantly optimizes multi-column structures at
the same time, which can result in the enormous redundant param-
eters among columns and overfitting on the limited training data.
To address these problems, our work aims to propose a general
learning strategy named Multi-column Mutual learning (McML) to
improve the learning of multi-column networks.

3.2 Overview of McML

In this section, we present an overview of Multi-column Mutual
Learning (McML) strategy. For the sake of simplicity, we introduce
the case of two columns as an example. As shown in Figure 3, our
McML has two main innovations.

e McML has integrated a statistical network into multi-column
structures to automatically estimate the mutual information
between columns. The essential of the statistical network is
a classifier network. Specifically, the inputs are features from
different columns, and the output is the mutual information
between columns. We use mutual information to approxi-
mately indicate the scale correlation between features from
different columns. By minimizing the mutual information
between columns, McML can guide each column to focus on
different image scale information.

e McML is a mutual learning scheme. Different from updating
the parameters of multiple columns simultaneously, McML
alternately optimizes each column in turn until the network
converged. In the learning of each column, the mutual infor-
mation between columns is first estimated as prior knowl-
edge to guide the parameter update. With the help of the
mutual information between columns, McML can alternately
make each column to be guided by other columns to learn
different image scales/resolutions. It is proved that this mu-
tual learning scheme can significantly reduce the volume of
redundant parameters and avoid overfitting.

  
 
  

 
   
  

Conv7-32
Maxpool
>

 

Conv9-16

 

 

Maxpool
>

 

 

 

 

Conv5-1
Stride=2

Column 6,

Conv7-16

   
 

Concatenate

®

Statistical Network

 

 

 

 

 

 

     

| | Conv5-40
7 Maxpool

Conv7-20

 
 

 

 

 

 

 

 

 

     

Convs-10

 

FC-128 = FC-1 #
> p34 Le
SPP 256
a Conv1-1 9
Concatenate

Column 6,

Figure 3: Overview of our Multi-column Mutual Learning (McML) strategy. It is equivalent to adding a statistical network to estimate the

mutual information Z,, between columns. By minimizing the mutual information, it can guide multi-columns to learn different scale infor-
mation. Additionally, McML is a mutual learning scheme as arrows © and ®@, where each column is alternately optimized while keeping the
other columns fixed on each mini-batch training data. Specifically, this is an example of two columns (©; and ©2) in MCNN [69]. ConvX-Y
implies a convolution layer has Y filters with XxX kernel size. The stride of all convolutional layers is 1, except for the special reminder.
MaxPool is the max pooling layer with a stride of 2. [Best viewed in color].

Mathematically, two columns with parameters 6; and @2 are
alternately trained as,

Lo, = min L2(Conv(F9, 06, (X)), Y) + adi(Co, ; Co,), (3)
1

Lo

2

= min L2(Conv(F9, 09, (X)), Y) + adi(Co, ;Co,)s (4)
2

where each column is trained by two losses. Lz loss (Eqn. 2) is
used to minimize counting errors, and I (Eqn. 7) is employed
to minimize the mutual information between columns. a is the
weight to trade off two losses. The value of mutual information Lo
is computed by the statistical network with parameters w. Here
we have slightly abused symbols. Cg, and Cg, are features from
different convolutional layers of two columns, which are used to
estimate the mutual information. Fg,.9,(X) means the ensemble
(ie., concatenation) of features at the last convolutional layers for
two both columns. Conv is a 1 X 1 convolutional layer that is used
to predict density maps for crowd counting.

Typically, our proposed McML is also a mutual learning scheme.
Two columns are alternately optimized until convergence. In the
learning of each column, the mutual information I, is first esti-
mated as prior knowledge to guide the parameter update. Once the
optimization of one column (e.g., 91) is finished, we will update the
mutual information J, again and alternately to update the other
column (e.g., 62). Additionally, it is noted that Eqns. 3 and 4 show the
situation of most multi-column networks (e.g., CrowdNet [3], AM-
CNN [68], and MCNN [69]), where the features of multi-columns
are concatenated to estimate density maps. However, a few multi-
column networks (e.g., ic-CNN [44]) predict density maps in all
columns. In these cases, Fg,.9, of Eqns. 3 and 4 should be replaced
with Fg, and Fg, respectively. Where Fg, and Fg, are features from
the last convolutional layers at two columns.

Specifically, we will introduce the mutual information estimation
(ie., computation of T,,) in Sec. 3.3, the mutual learning scheme in
Sec. 3.4 and neural architectures of statistical networks in Sec. 3.5.

3.3. Mutual Information Estimation

In this section, we first briefly introduce the definition of mutual
information. Then we present the statistical network in details.
Mutual information is a fundamental quantity for measuring the
correlation between variables. We treat column structures as dif-
ferent variables. Inspired by the success of previous works [28, 38],
we use mutual information to indicate the degree of parameter
redundancy between columns. Moreover, mutual information can
also approximately measure the scale correlation between features
from different columns. Instead of estimating the mutual informa-
tion with parameters of columns, similar to [6, 15, 20], we chooses
to compute the mutual information using the features of multi-
columns since our objective is to learn different scale features.
Typically, the mutual information between features Cg, and Cg, is

defined as,
I(Co,;Co,) = H(Ce,) - H(Ca, | Co,): (5)

where H is the Shannon entropy. H(Cg, | Cg,) measures the uncer-
tainty in Cg, given Cg,. Previous works [6, 28, 38, 42] widely use
Kullback-Leibler (KL) divergence to compute the mutual informa-
tion,

L(Cg,;Co,) = DKL(P cy, Co, || Peo, ® Pco,)s (6)
where PC, Co, is the joint distribution of two features. PCo, and

Pcp
2
the joint distribution Pcp, Co, and the product of marginal distribu-

are the marginal distributions. ® means the production. Since

tions Peg, @ Peo, are unknown in our case, the mutual information
of two columns is challenging to compute [40].

Fortunately, inspired by the previous work named MINE [2], we
propose a statistical network to estimate the mutual information.
The essence of the statistical network is a classifier. It can be used
to distinguish the samples between the joint distribution and the
product of marginal distributions. Instead of computing Eqn. 6, the
statistical network chooses to use Donsker-Varadhan representa-
tion [18] ie., (Cg,;Cg,) = T..(Co,;Co,); to get a lower-bound for

Algorithm 1 Mutual Information Estimation

Algorithm 2 Mutual Learning Scheme

 

 

Input: Randomly sampled b images.
1: Draw features from two columns as the joint distribution,
2: (c Cc) (c) ct) ~Pp .
Ma? 0,7? 0, > Co, Co,’
3: Randomly disrupt Cg, as the product of marginal distribution,
(eM o@ (b) Alb) .
4: (Col, Co), ---» (Co's Co,) ~ Peo, @ Peg, ;
: Evaluate mutual information £,, Das Eqn. 7;
: Use moving average to get the gradient,
» Ge) — Velo:
: Update the statistical network parameters,
oO — aot Gla);

Oo OID

 

the mutual information estimation,

_ b yo b (i) B®,
By — FY TolCh,Cy)) = logs e700, 7)
i=1 i=1

where T,, is the statistical network with parameters w. To com-
pute the lower-bound I, we randomly select b training images.
With the forward pass of the network, we directly get b pairs
of features from two column structures as the joint distribution
(Ce,,Ce,) ~ PC, Co," At the same time, we randomly disrupt the
order of Cg, in (Cg,.Cg,) ~ PC, Co, to get b pairs of features as

the product of the marginal distribution (Cg,, Co,) ~ Peg, @ Peg, :
Then we input these features to the statistical network T,,. By cal-
culating the b outputs of the statistical network as Eqn. 7, we can
get a lower-bound for the mutual information estimation. Here we
use moving average to get the gradient of Eqn. 7. By maximizing
this lower-bound, we can approximately obtain the real mutual
information. More details of the mutual information estimation are
provided in Alg. 1.

Without loss of generality, the statistical network T,, can be
designed as any classifier networks according to the different multi-
column networks. We have tested McML on three multi-column
networks (i.e., MCNN [69], CSRNet [30] and ic-CNN [44]). The
statistical networks for these baselines are described in Sec. 3.5.

3.4 Mutual Learning Scheme

Our proposed McML is a mutual learning scheme. For the sake of
simplicity, we present the case of two columns as an example. As
shown in Alg. 2, we alternately optimize two columns in each mini-
batch until convergence. In each learning iteration, we randomly
sample b training images. Before optimizing column 0, the mutual
information is first estimated as prior knowledge to guide the pa-
rameter update. With forward of the network, the features of two
column structures are sampled to update the statistical network T,,
and estimate the mutual information J, as Alg. 1. With the guid-
ance of the mutual information, our McML can supervise column 6;
to learn as much as possible different scale features from column 62.
It is noted that we have fixed parameters of other columns (i.e., 02)
and statistical network (T,,), and only update column 0. Since the
size of input images are different, we have to update column struc-
ture on each image. After back-propagation of a total of b images,
the column 2 will be optimized in similar steps.

It is noted that our McML can be naturally extended to multi-
columns architectures. For the case of K > 2, the loss function of a

Input: Training set X, Ground truth Y.
1: 01, @2 and w < initialize network parameters;
2: repeat
3: Randomly sampled b images from X;
4: Estimate mutual information r, and update statistical network T,,

 

as Alg. 1;
5: Update column 6, as Eqn. 3 on each image,
Lo,
6: 0, — 0, + OO,
7: Estimate mutual information J, and update statistical network T,,
as Alg. 1;
8: Update column @2 as Eqn. 4 on each image,
Lo,
9: 02 — 02 + 00”?

10: until Convergence

 

column 6; is computed as,

K =
Dd Fo(Co,5 Ca):
l=1,k#l
(8)

Similar to Eqns. 3 and 4, where Fg, 09,,..,6, means the ensemble (i.e.,
concanation) of features from the last convolutional layers at multi-
columns. Cg, is the features from different convolutional layers at
each column. a is a weight to trade off two losses. At this point,
we only need to add more steps to estimate mutual information
of multi-columns. Once the mutual information is obtained, multi-

 

a
Lo, = Le(Conv( Fo, 06), .., 0x (X)), Y) + K

column structures are still alternately optimized until convergence.

3.5 Network Architectures

We employ McML to improve three state-of-the-art networks, in-
cluding MCNN [69], CSRNet [30], and ic-CNN [44]. Table 2 shows
the neural architecture of statistical networks. To better under-
stand the details, Figure 3 gives a real example of two columns in
MCNN [69]. With sharing the parameters, no matter how many
columns are adopted, each multi-column network only needs one
single statistical network. The inputs of statistical networks are the
features from different layers. We use convolutional layers with
one output channel to reduce the feature dimension. Since training
images have different size and inspired by the previous work [14],
one spatial pyramid pooling (SPP) layer is applied to reshape the
features from the last convolutional layer into a fixed dimension.

Table 2: The structure of statistical network. The convolutional,
spatial pyramid pooling, and fully connected layers are denoted as
"Conv (kernel size)-(number of channels)-(stride)", "SPP (size of out-
puts)", and "FC (size of outputs)".

 

 

 

MCNN [69] | CSRNet [30] | ic-CNN [44]
Conv 5-1-2 Conv 3-1-1 Conv 3-1-1
Conv 3-1-2 Conv 3-1-1 Conv 3-1-1
Conv 3-1-1 Conv 3-1-1 Conv 3-1-1
Conv 3-1-1 Conv 3-1-1 Conv 3-1-1
SPP 256 Conv 3-1-1 Conv 3-1-1
FC 128 Conv 3-1-1 SPP 256
FC 1 SPP 256 FC 128

FC 128 FC 1

FC 1

 

 

 

 

 

Table 3: Performance of ablation studies. Comparison of Org. (Original Baseline), MLS (Mutual Learning Scheme), MIE (Mutual
Information Estimation), and McML (Multi-column Mutual Learning) on four crowd counting datasets.

 

 

 

 

 

 

 

 

 

 

 

ShanghaiTech A [69] | ShanghaiTech B [69] | UCF_CC_50[24] | UCSD[65] | WorldExpo’10 [8]
Method MAE MSE MAE MSE MAE MSE MAE MSE MAE
MCNN [69] 110.2 173.2 26.4 41.3 377.6 509.1 1.07 1.35 11.6
MCNN+MLS 105.2 160.3 22.2 34.2 332.8 425.3 1.04 1.35 10.8
MCNN+MIE 106.7 160.5 25.4 35.6 338.6 447.4 1.12 1.47 11.0
MCNN+McML 101.5 157.7 19.8 33.9 311.0 402.4 1.03 1.24 10.2
CSRNet [30] 68.2 115.0 10.6 16.0 266.1 397.5 1.16 1.47 8.6
CSRNet+MLS 64.2 109.3 9.9 12.3 254.2 376.3 1.00 1.31 8.4
CSRNet+MIE 65.6 111.0 9.3 12.8 264.9 387.1 1.06 1.40 8.3
CSRNet+McML 59.1 104.3 8.1 10.6 246.1 367.7 1.01 1.27 8.0
ic-CNN [44] 68.5 116.2 10.7 16.0 260.9 365.5 1.14 1.43 10.3
ic-CNN+MLS 67.4 112.8 10.3 14.6 248.4 364.3 1.02 1.28 9.7
ic-CNN+MIE 66.3 111.8 11.3 15.1 255.3 368.2 1.06 1.34 9.8
ic-CNN+McML 63.8 110.5 10.1 13.9 242.9 357.0 1.00 1.20 8.5

 

 

 

 

 

Finally, two fully connected layers are employed as a classifier. Sim-
ilar to [2], Leaky-ReLU [37] is used as the activation function for all
convolutional layers, and no activation function for other layers.

Specifically, MCNN adopts 3 column structures. Each column
contains 4 convolutional layers. Intuitively, the statistical network
of MCNN uses 4 convolutional layers to embed the features as
Figure 3. CSRNet is a single column network. The first 10 convolu-
tional layers are from pre-trained VGG-16 [54]. The last 6 dilated
convolutional layers are utilized to estimate the crowd counts. The
original version has 4 configurations for 6 dilated convolutional
layers (i.e., different dilation rates). Here we treat 4 configurations
as 4 different columns. Similarly, as shown in Table 2, the statistical
network of CSRNet utilizes 6 convolutional layers to embed the
features for 6 dilated convolutional layers in each column. ic-CNN
contains two columns (i.e., Low Resolution (LR) and High Reso-
lution (HR) columns). LR contains 11 convolutional layers and 2
max-pooling layers, and HR has 10 convolutional layers with 2
max-pooling layers and 2 deconvolutional layers. As Table 2 shows,
the statistical network of ic-CNN uses 5 convolutional layers to
embed features from corresponding 5 convolutional layers after the
second max pooling layer at both columns.

4 EXPERIMENT
4.1 Experiment Settings

Datasets. To evaluate the effectiveness of our McML, we con-
duct experiments on four crowd counting datasets, ie., Shang-
haiTech [69], UCF_CC_50 [24], UCSD [8], and WorldExpo’10 [65].
Specifically, ShanghaiTech dataset consists of two parts: Part_A
and Part_B. Part_A is collected from the internet and usually has
very high crowd density. Part_B is from busy streets and has a rela-
tively sparse crowd density. UCF_CC_50 is mainly collected from
Flickr and contains images of extremely dense crowds. UCSD and
WorldExpo’10 are both collected from actual surveillance cameras
and have low resolution and sparse crowd density. More details of
datasets split are illustrated in supplementary material.

Learning Settings. We use our McML to improve MCNN, CSRNet,
and ic-CNN. For MCNN, the network is initiated by a Gaussian
distribution with a mean of 0 and a standard deviation of 0.01.
Adam optimizer [27] with a learning rate of 1e-5 is used to train
three columns. For CSRNet, the first 10 convolutional layers are

fine-tuned from the pre-trained VGG-16 [54]. The other layers are
initiated in the same way as MCNN. We use Stochastic gradient
descent (SGD) with a fixed learning rate of 1e-6 to finetune four
columns. For ic-CNN, input features from Low-resolution column to
High-resolution column are neglected. The SGD with the learning
rate of 1e-4 is used to train two columns. The learning settings of
the statistical network for all baselines are the same. The number
of samples b is 75. Moving average is used to evaluate gradient bias.
Adam optimizer with a learning rate of 1e — 4 is used to optimize
the statistical network. More details of ground truth generation and
data augmentation are illustrated in supplement materials.
Evaluation Details. Following previous works [30, 44, 69], we
use mean absolute error (MAE) and mean square error (MSE) to
evaluate the performance:

N
1
- > . gt =
MAE = =& |zi - 23 |. MSE =

i=1

 

where Z; is the estimated crowd count and Zz ’ is the ground truth
count of the i-th image. N is the number of test images. The MAE
indicates the accuracy of the estimation, while the MSE indicates
the robustness.

4.2 Ablation Studies

We have conduct extensive ablation studies on our McML.

MIE vs. MLS. We separately investigate the roles of our proposed
two improvements, i.e., Mutual Learning Scheme (MLS) and Mutual
Information Estimation (MIE). Experimental results are shown in
Table 3. Org. is the original baseline, MLS means that we ignore the
mutual information estimation (i.e., T w) in Eqns. 3 and 4, and MIE
indicates that we optimize all columns at the same time (ie., do
not alternately optimize each column). Generally speaking, MLS
achieves better performance than all original baselines. After inte-
grated MIE, there is a noticeable improvement. It fully demonstrates
the effectiveness of our method.

Statistical Network. We intend to compare different statistical
networks. We have modified the proposed statistical network as fol-
lows: 1) Only-1-Conv means only keep the last convolutional layer.
2) Last-3-Conv denotes to preserve the last three convolutional lay-
ers. 3) First-3-Conv indicates to retain the first three convolutional
layers. 4) FC-3 (64) means to add one fully connected (FC) layer
with 64 outputs between the original two FC layers. 5) FC-1 (64)

Table 4: Comparison with state-of-the-art methods on ShanghaiTech [69], UCF_CC_50 [24] and UCSD [65] datasets.

 

 

 

 

 

 

 

 

 

ShanghaiTech A [69] | ShanghaiTech B [69] | UCF_CC_50 [24] UCSD [65]
Method Venue & Year | MAE MSE MAE MSE MAE MSE MAE MSE
Idrees et al. [24] | CVPR 2013 - - - - 419.5 541.6 - -
Zhang et al. [65] CVPR 2015 181.8 277.7 32.0 49.8 467.0 498.5 1.60 3.31
CCNN [39] ECCV 2016 - - - - - - 1.51 -
Hydra-2s [39] ECCV 2016 - - - - 333.7 425.3 - -
C-MTL [55] AVSS 2017 101.3 152.4 20.0 31.1 322.8 397.9 - -
SwitchCNN [50] CVPR 2017 90.4 135.0 21.6 33.4 318.1 439.2 1.62 2.10
CP-CNN [56] ICCV 2017 73.6 106.4 20.1 30.1 295.8 320.9 - -
Huang at al. [23] | TIP 2018 - - 20.2 35.6 409.5 563.7 1.00 1.40
SaCNN [66] WACV 2018 86.8 139.2 16.2 25.8 314.9 424.8 - -
ACSCP [51] CVPR 2018 75.7 102.7 17.2 27.4 291.0 404.6 - -
IG-CNN [49] CVPR 2018 72.5 118.2 13.6 21.1 291.4 349.4 - -
Deep-NCL [53] CVPR 2018 73.5 112.3 18.7 26.0 288.4 404.7 - -
MCNN [69] CVPR 2016 110.2 173.2 26.4 41.3 377.6 509.1 1.07 1.35
CSRNet [30] CVPR 2018 68.2 115.0 10.6 16.0 266.1 397.5 1.16 1.47
ic-CNN [44] ECCV 2018 68.5 116.2 10.7 16.0 260.9 365.5 1.14 1.43
MCNN+McML - - 101.5 157.7 19.8 33.9 311.0 402.4 1.03 1.24
CSRNet+McML - - 59.1 104.3 8.1 10.6 246.1 367.7 1.01 1.27
ic-CNN+McML - - 63.8 110.5 10.1 13.9 242.9 357.0 1.00 1.20

 

 

 

 

 

indicates to reduce the outputs of the first FC layer into 64. 6) FC-1
(256) states to increase the outputs of the first FC layer into 256.
Comparison results are illustrated in Table 6. In general, different
statistical networks have no significant difference in performance.
Even using only one convolutional layer, our proposed training
strategy still obviously improve the original baseline. These results
fully demonstrate the robustness of our method.

The number of samples b. We study the effect of the number of
samples b. As shown in Figure 4, we obverse that with the number
of b increases, the performance first increases and then decreases.
Typically, when b is too small, because of the estimated mutual
information has a severe bias, our method intuitively gets poor
performance. In contrast, when bD is too large, although the mutual
information has been accurately estimated, the performance of our
model is still severely affected since the iterations of the mutual
learning scheme are inadequate. Based on that we use a binary
search to find the best value of b. After extensive cross-validation,
b is set to 75 for all baselines.

The weight of a. We have verified the impact of the weight of a.
To get a more accurate setting, we perform a grid search with the
step of 0.1. The best values of a for different datasets are illustated
in Table 5. Since ShanghaiTech Part A and UCF_CC_50 have more
substantial scale changes, they have a larger @ than other datasets.
We assume that the weight of a positively correlates to the degree
of scale changes.

 

 

.

 

 

 

 

 

110 Datasets a
a ‘be = ShanghaiTech A | 0.3
5 104 a —_ ShanghaiTech B | 0.2
‘0 — UCF_CC_50 0.4
98 ‘ UCSD 0.1
2 50 75 700 ;
The Number of Samples b WorldExpo 10 0.2

 

 

 

 

Figure 4: Effects of samples b. Table 5: The values of a.

Table 6: Ablation studies of statistical networks on ShanghaiTech
Part A dataset [69].

 

 

 

 

 

 

 

 

MCNN [69] | CSRNet [30] | ic-CNN [44]
Structures MAE | MSE | MAE | MSE | MAE | MSE
Only-1-Conv 104.2 | 160.8 61.7 106.9 66.2 114.1
Last-3-Conv 103.5 | 160.1 61.1 106.8 65.5 113.3
First-3-Conv 103.2 | 159.7 60.7 106.1 64.8 113.2
FC-3 (64) 101.6 | 157.8 59.3 104.3 | 63.9 110.5
FC-1 (64) 102.0 | 158.2 59.8 105.1 64.5 111.3
FC-1 (256) 102.2 | 158.4 59.7 104.8 63.9 111.0
Ours (Table 2) | 101.5 | 157.7 | 59.1 | 104.3 | 63.8 | 110.5

 

 

 

 

 

4.3 Comparisons with State-of-the-art

We demonstrate the efficiency of our McML on four challenging
crowd counting datasets. Tables 4 and 7 show the comparison with
the other state-of-the-art methods. We observe that McML can
significantly improve three baselines (i.e., MCNN, CSRNet, and
ic-CNN) on all datasets. Notably, after using McML, the optimized
CSRNet and ic-CNN also obviously outperform the other state-
of-the-art approaches. It fully demonstrates that our method can
not only be applied to any multi-column network but also works
on both dense and sparse crowd scenes. Additionally, although
ic-CNN also propose an alternate training process, our McML can
still achieve better results than the original ic-CNN. It means that
our McML is more effective than ic-CNN.

For ShanghaiTech dataset, McML significantly boosts MCNN,
CSRNet, and ic-CNN with relative MAE improvements of 7.9%,
13.3% and 6.9% on Part A, and 25.0%, 23.6% and 5.6% on Part B,
respectively. Similarly, for UCF_CC_50 dataset, McML provides the
relative MAE improvements of 17.6%, 7.5%, and 6.9% for three base-
lines. These results clearly state McML can not only handle dense-
crowd scenes but also work for small datasets. On the other hand,
experimental results of UCSD dataset show McML can improve the
accuracy (i.e., lower MAE) and gain the robustness (i.e., lower MSE).
This result states the effectiveness of McML on the sparse-crowd
scene. Additionally, on WorldExpo’10 dataset, although our pro-
posed McML does not utilize perspective maps, they still achieve

Col.3+

Oa

865
RE

 

Table 7: Comparison with state-of-the-art methods on World-
Expo’10 [8] dataset. Only MAE is computed for each scene and then
averaged to evaluate the overall performance.

 

Method S1 $2 $3 S4 | S5 | Avg.
Zhang et al. [65] 9.8 14.1 | 14.3 | 22.2 | 3.7 12.9
Huang et al. [23] 41 21.7 | 11.9 | 11.0 | 3.5 10.5
Switch-CNN [50] 4.4 15.7 | 10.0 | 11.0 | 5.9 9.4

 

 

 

SaCNN [66] 2.6 13.5 | 10.6 | 12.5 | 3.3 8.5
CP-CNN [56] 2.9 14.7 | 10.5 | 10.4 | 5.8 8.9
MCNN [69] 3.4 20.6 | 12.9 | 13.0 | 8.1 11.6
CSRNet [30] 2.9 11.5 8.6 16.6 | 3.4 8.6
ic-CNN [44] 17.0 | 12.3 9.2 8.1 4.7 10.3
MCNN+McML 3.4 15.2 | 14.6 | 12.7 | 5.2 10.2

CSRNet+McML 2.8 | 11.2 | 9.0 13.5 | 3.5 8.0
ic-CNN+McML 10.7 | 11.2 | 8.2 8.0 | 4.5 8.5

 

 

 

 

 

 

 

 

 

better results than other state-of-the-art methods that use perspec-
tive maps.

4.4 Why does McML Work

We attempt to give more insights to show why our McML works.
The statistical analysis is illustrated in Table 8. Compared with
the results without McML (in Table 1), we observe that McML can
significantly reduce Maximal Information Coefficient (MIC) and
Structural SIMilarity (SSIM) between columns. It denotes that our
method can indeed reduce the redundant parameters of columns
and avoid overfitting. On the other hand, McML can efficiently
improve MIC and SSIM between the ensemble of all columns and
the ground truth. It means that our method can guide multi-column
structures to learn different scale features and improve the accuracy
of crowd counting.

To further verify that our McML can indeed guide multi-column
networks to learn different scales, we showcase the generated den-
sity maps from different columns of MCNN in Figure 5. These four
examples typically contain different crowd densities, occlusions,
and scale changes. We observe that estimated density maps of
McML have more different salient areas than the original MCNN. It
means that our method can indeed guide multi-column structures
to focus on different scale information (ie., different people/head
sizes). It is noted that the ground truth itself is generated with center
points of pedestrians’ heads, which inherently contains inaccurate
information. Thus the result of our method is still unable to produce
the same density map to the ground truth.

Figure 5: Comparison of estimated density maps between MCNN [69] and McML. ‘+’ indicates employing McML on the original MCNN.

Table 8: The result analysis of our proposed McML. The values in
the table are the average of all columns. Col.<>Col. is the result be-
tween different columns. Col.GT is the result between the ensem-
ble of all columns and the ground truth.

 

Col.© Col. Col. GT
Method MIC | SSIM | MIC | SSIM

ShanghaiTech Part A [69]
MCNN+McML 0.74 0.61 0.68 0.70
CSRNet+McML 0.77 0.70 0.82 0.82
ic-CNN+McML 0.76 0.55 0.80 0.76
UCE CC _50 [24]
MCNN+McML 0.69 0.48 0.79 0.47
CSRNet+McML 0.73 0.60 0.75 0.61
ic-CNN+McML 0.75 0.60 0.72 0.64

5 CONCLUSION

In this paper, we propose a novel learning strategy called Multi-
column Mutual learning (McML) for crowd counting, which can
improve the scale invariance of feature learning and reduce pa-
rameter redundancy to avoid overfitting. It could be applied to all
existing CNN-based multi-column networks and is end-to-end train-
able. Experiments on four challenging datasets fully demonstrate
that it can significantly improve all baselines and outperforms the
other state-of-the-art methods. In summary, this work provides the
elegant views of effectively using multi-column architectures to
improve the scale invariance. In future work, we will study how to
handle different image scales and resolutions in the ground truth
generation.

6 ACKNOWLEDGEMENTS

This research was supported in part through the financial assistance award
60NANB17D156 from U.S. Department of Commerce, National Institute
of Standards and Technology and by the Intelligence Advanced Research

 

 

 

 

 

 

 

 

 

 

 

 

 

 

Projects Activity (ARPA) via Department of Interior/Interior Business
Center (DOI/IBC) contract number D17PC00340, National Natural Science
Foundation of China (Grant No: 61772436), Foundation for Department
of Transportation of Henan Province, China (2019J-2-2), Sichuan Science
and Technology Innovation Seedling Fund (2017RZ0015), China Scholar-
ship Council (Grant No. 201707000083) and Cultivation Program for the
Excellent Doctoral Dissertation of Southwest Jiaotong University (Grant
No. D-YB 201707).

