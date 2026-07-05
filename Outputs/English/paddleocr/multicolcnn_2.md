An Aggregated Multicolumn Dilated Convolution Network
for Perspective-Free Counting
Diptodip Deb
Jonathan Ventura
Georgia Institute of Technology
University of Colorado Colorado Springs
diptodipdeb@gatech.edu
jventura@uccs.edu
8
2018
Abstract
counting cells in a microscope image, pedestrians in a
crowd, or vehicles in a traffic jam, regressors trained on a
Apr
We propose the use of dilated filters to construct an ag-
single image scale are not reliable [18]. This is due to a
variety of challenges including overlap of objects and per-
gregation module in a multicolumn convolutional neural
spective effects which cause significant variance in object
network for perspective-free counting. Counting is a com-.
20
mon problem in computer vision (e.g. traffic on the street or
shape, size and appearance.
pedestrians in a crowd). Modern approaches to the count-
The most successful recent approaches address this issue
ing problem involve the production of a density map via re-
by explicitly incorporating multi-scale information in the
gression whose integral is equal to the number of objects
network [18 28]. These approaches either combine multiple
in the image. However, objects in the image can occur at
networks which take input patches of different sizes [18]
different scales (e.g. due to perspective effects) which can
 or combine multiple filtering paths ("columns") which have
different size filters [28].
density map. While the use of multiple columns to extract
Following on the intuition that multiscale integration is
multiscale information from images has been shown be-
key to achieving good counting performance, we propose
A
fore, our approach aggregates the multiscale information.
to incorporate dilated filters [25] into a multicolumn con-
gathered by the multicolumn convolutional neural network.
volutional neural network design [28]. Dilated filters expo-
2
to improve performance. Our experiments show that our
nentially increase the network's receptive field without an
8
proposed network outperforms the state-of-the-art on many
exponential increase in parameters, allowing for efficient.
7
benchmark datasets, and also that using our aggregation
use of multiscale information. Convolutional neural net-
L804.
module in combination with a higher number of columns is
works with dilated filters have proven to provide compet-
beneficial for multiscale counting.
itive performance in image segmentation where multiscale
analysis is also critical [25][26]. By incorporating dilated
filters into the multicolumn network design, we greatly in-
lv:1
1. Introduction
crease the ability of the network to selectively aggregate
multiscale information, without the need for explicit per-
arXi
Learning to count the number of objects in an image is a
spective maps during training and testing. We propose the
deceptively difficult problem with many interesting applica-
aggregated multicolumn dilated convolution network"' or
tions, such as surveillance [20], traffic monitoring [14] and
AMDCN which uses dilations to aggregate multiscale in-
medical image analysis [22]. In many of these application
formation. Our extensive experimental evaluation shows
areas, the objects to be counted vary widely in appearance,
that this proposed network outperforms previous methods
size and shape, and labeled training data is typically sparse.
 on many benchmark datasets.
These factors pose a significant computer vision and ma-
chine learning challenge.
2. Related Work
Lempitsky et al. [15] showed that it is possible to learn to
count without learning to explicitly detect and localize in-
Counting using a supervised regressor to formulate a
dividual objects. Instead, they propose learning to predict a
density map was first shown by [15]. In this paper, Lem-
density map whose integral over the image equals the num-
pitsky et al. show that the minimal annotation of a single
ber of objects in the image. This approach has been adopted
dot blurred by a Gaussian kernel produces a sufficient den-
by many later works (Cf. [18]28]).
sity map to train a network to count. All of the counting
However, in many counting problems, such as those
methods that we examine as well as the method we use in.
1
columns
5x5
3x3
1x1
aggregator
D
3x3
qunos = x 
x E D
Figure 1. Fully convolutional architecture diagram (not to scale). Arrows show separate columns that all take the same input. At the end
which can aggregate the multiscale information collected by the columns [25]. The input image is I with C channels. The output single.
channel density map is D, and integrating over this map (summing the pixels) results in the final count. Initial filter sizes are labeled with
brackets or lines. Convolution operations are shown as flat rectangles, feature maps are shown as prisms. The number below each filter
represents the dilation rate (1 means no dilation).
our paper follow this method of producing a density map
of the image is truly necessary in order to solve dense pre-
via regression. This is particularly advantageous because a
diction problems via convolutional neural networks. More-
sufficiently accurate regressor can also locate the objects in
over, these approaches seem to saturate in performance at
the image via this method. However, the Lempitsky paper
three columns, which means the network is extracting in-.
ignores the issue of perspective scaling and other scaling
formation from fewer scales. The work of [25] proposes
issues. The work of [27] introduces CNNs (convolutional
the use of dilated convolutions as a simpler alternative that.
neural networks) for the purposes of crowd counting, but.
does not require sampling of rescaled image patches to pro-
performs regression on similarly scaled image patches.
vide global, scale-aware information to the network. A fully
These issues are addressed by the work of [18]. Rubio
convolutional approach to multiscale counting has been pro-
et al. show that a fully convolutional neural network can be
posed by [28], in which a multicolumn convolutional net-
work gathers features of different scales by using convolu-
used to produce a supervised regressor that produces den-.
sity maps as in [15]. They further demonstrate a method
tions of increasing kernel sizes from column to column in-
dubbed HydraCNN which essentially combines multiple
stead of scaling image patches. Further, DeepLab has used
convolutional networks that take in differently scaled im-
dilated convolutions in multiple columns to extract scale
age patches in order to incorporate multiscale, global in-
formation from the image. The premise of this method is
proaches with our aggregator module as described in Sec-
that a single regressor will fail to accurately represent the
tion[3.1 which should allow for extracting information from
difference in values of the features of an image caused by
more scales.
perspective shifts (scaling effects) [18]
It should be noted that other methods of counting exist,
However, the architectures of both [18] and [27] are not
including training a network to recognize deep object fea-
fully convolutional due to requiring multiple image patches
tures via only providing the counts of the objects of interest
and, as discussed in [25], the experiments of [11]17] and
in an image [21] and using CNNs (convolutional neural net-
12[16] leave it unclear as to whether rescaling patches
works) along with boosting in order to improve the results
operation as defined in [25] is given by
(F*k)(p) =
> F(s)k(t)
(1)
s+t=p
A dilated convolution is essentially a generalization of
the traditional 2D convolution that allows the operation to
skip some inputs. This enables an increase in the size of
Figure 2. UCF sample results. Left: input counting image. Mid
the filter (i.e. the size of the receptive field) without los-
dle: Ground truth density map. Right: AMDCN prediction of
ing resolution. Formally, we define from [25] the dilated
density map on test image. The network never saw these im-
convolution as
ages during training. All density maps are one channel only (i.e.
grayscale), but are colored here for clarity.
(F*ik)(p)=  F(s)k(t)
(2)
s+lt=p
of regression for production of density maps [24]. In the
where l is the index of the current layer of the convolution.
same spirit, [4] combines deep and shallow convolutions
Using dilations to construct the aggregator in combi-
within the same network, providing accurate counting of
nation with the multicolumn idea will allow for the con-
dense objects (e.g. the UCF50 crowd dataset).
struction of a network with more than just 3 or 4 columns
In this paper, however, we aim to apply the dilated con-
as in [28] and [8], because the aggregator should prevent
volution method of [25], which has shown to be able to in-
corporate multiscale perspective information without using
the saturation of performance with increasing numbers of
columns. Therefore the network will be able to extract use.
multiple inputs or a complicated network architecture, as
ful features from more scales. We take advantage of dila-
well as the multicolumn approach of [8]28] to aggregate
tions within the columns as well to provide large receptive
multiscale information for the counting problem.
fields with fewer parameters.
Looking at more scales should allow for more accurate
3. Method
regression of the density map. However, because not all.
3.1. Dilated Convolutions for Multicolumn Net-
scales will be relevant, we extend the network beyond a
works
simple 1  1 convolution after the merged columns. In-
stead, we construct a second part of the network, the aggre-
We propose the use of dilated convolutions as an at-
gator, which sets our method apart from [28], [8], and other
tractive alternative to the architecture of the HydraCNN.
multicolumn networks. This aggregator is another series of.
[18], which seems to saturate in performance at 3 or more
dilated convolutions that should appropriately consolidate
columns.We refer to our proposed network as the ag-
the multiscale information collected by the columns. This
gregated multicolumn dilated convolution network hence-
is a capability of dilated convolutions observed by [25]
forth shortened as the AMDCN. The architecture of the.
While papers such as [28] and [8] have shown that multiple
AMDCN is inspired by the multicolumn counting network
columns and dilated columns are useful in extracting multi-
of [28]. Extracting features from multiple scales is a good
scale information, we argue in this paper that the simple ag-
idea when attempting to perform perspective-free counting
gregator module built using dilated convolutions is able to
and increasing the convolution kernel size across columns
effectively make use multiscale information from multiple
is an efficient method of doing so. However, the number.
columns. We show compelling evidence for these claims in
Section4.5
used in these columns to extract features at larger scales.
The network as shown in Figurecontains 5 columns.
Therefore, we propose using dilated convolutions rather
Note that dilations allow us to use more columns for count-
than larger kernels..
Dilated convolutions, as discussed in [25], allow for the
the previous (the exact dilations can also be seen in Figure
exponential increase of the receptive field with a linear in-
1). There are 32 feature maps for each convolution, and all
crease in the number of parameters with respect to each hid-
den layer.
to maintain the same data shape from input to output. That
In a traditional 2D convolution, we define a real valued
is, an image input to this network will result in a density
function F : Z2 > R, an input Q, = [-r, r]2 e Z2, and
map of the same dimensions. All activations in the speci-
a filter function k : r -> R. In this case, a convolution
fied network are ReLUs. Our input pixel values are floating
point 32 bit values from O to 1. We center our inputs at O by
1 Implementation
 available
https://github.com/
on
diptodip/counting
subtracting the per channel mean from each channel. When
training, we use a scaled mean absolute error for our loss
Furthermore, we performed a set of experiments in
which we varied the number of columns from 1 to 5 (sim-
function:
ply by including or not including the columns as specified in
`|yi-YYi|
(3)
Figure[1 starting with the smallest filter column and adding
where  is the scale factor, yi is the prediction, yi is the true
is allowed to extract information at larger and larger scales
value, and n is the number of pixels. We use a scaled mean
in addition to the smaller scales as we include each column.
absolute error because the target values are so small that it
We then performed the same set of experiments, varying
is numerically unstable to regress to these values. At testing
the number of columns, but with the aggregator module re-
time, when retrieving the output density map from the net-
moved. We perform these experiments on the original split
work, we scale the pixel values by -1 to obtain the correct
of UCSD as specified in Section3.2.3and [5], the TRAN-
value. This approach is more numerically stable and avoids
COS dataset, and the WorldExpo dataset because these are
having the network learn to output only zeros by weight-
relatively large and well defined datasets. We limit the num-
ing the nonzero values highly. For all our datasets, we set
ber of epochs to 10 for all of these sets of experiments in or-
y = 255.
der to control for the effect of learning time, and also com-
pare all results using MAE for consistency. These experi-
3.2. Experiments
ments are key to determining the efficacy of the aggregator
in effectively combining multiscale information and in pro-
We evaluated the performance of dilated convolutions
viding evidence to support the use of multiple columns to
against various counting methods on a variety of common
extract multiscale information from images. We report the
counting datasets: UCF5O crowd data, TRANCOS traffic
results of these ablation studies in Section4.5]
data [18], UCSD crowd data [5], and WorldExpo crowd
data [27]. For each of these data sets, we used labels given
3.2.1UCF50 Crowd Counting
by the corresponding density map for each image. An ex-
ample of this is shown in Figure 2 We have performed
UCF is a particularly challenging crowd counting dataset.
experiments on the four different splits of the UCSD data
There are only 50 images in the whole dataset and they are
as used in [18] and the split of the UCSD data as used
all of varying sizes and from different scenes. The number
in [28] (which we call the original split). We also evaluated
of people also varies between images from less than 100
the performance of our network on the TRANCOS traffic
to the thousands. The average image has on the order of
dataset [14]. We have also experimented with higher den-
1000 people. The difficulty is due to the combination of the
sity datasets for crowd counting, namely WorldExpo and
very low number of images in the dataset and the fact that
UCF.
the images are all of varying scenes, making high quality
We have observed that multicolumn dilations produce
generalization crucial. Furthermore, perspective effects are
density maps (and therefore counts) that often have lower
particularly noticeable for many images in this dataset. De-
loss than those of HydraCNN [18] and [28]. We measure
spite this, there is no perspective information available for
density map regression loss via a scaled mean absolute error
this dataset.
loss during training. We compare accuracy of the counts via
We take 1600 random patches of size 150  150 for the
mean absolute error for the crowd datasets and the GAME
training. For testing, we do not densely scan the image as
metric in the TRANCOS dataset as explained in Section
in [18] but instead test on the whole image. In order to
3.2.2 Beyond the comparison to HydraCNN, we will also
standardize the image sizes, we pad each image out with
compare to other recent convolutional counting methods,
zeros until all images are 1024  1024. We then suppress
especially those of [21], [24], and [4] where possible.
output in the regions where we added padding when testing.
For all datasets, we generally use patched input images
This provides a cleaner resulting density map for these large
e nunnnnn nq pnnnnnnd sdnn nnnrnnp mnn punnnn pud
crowds. The ground truth density maps are produced by
Gaussian of a fixed size (o) for each object for training.
annotating each object with a Gaussian of o = 15.
This size varies from dataset to dataset, but remains constant
within a dataset with the exception of cases in which a per-
3.2.2TRANCOS Traffic Counting
spective map is used. This is explained per dataset. All ex-
periments were performed using Keras with the Adam opti-
TRANCOS is a traffic counting dataset that comes with its
mizer [10]. The learning rates used are detailed per dataset.
own metric [14]. This metric is known as GAM E, which
For testing, we also use patches that can either be directly
stands for Grid Average Mean absolute Error. GAME
pieced together or overlapped and averaged except in the
splits a given density map into 4 grids, or subarrays, and
case of UCF, for which we run our network on the full im-
obtains a mean absolute error within each grid separately.
age.
The value of L is a parameter chosen by the user. These
individual errors are summed to obtain the final error for a
"minimal,' and "downscale. We see in Table 3|that the
particular image. The intuition behind this metric is that it
"upscale' split and "downscale"' split give us state of the
is desirable to penalize a density map whose overall count
art results on counting for this dataset. For this experiment,
might match the ground truth, but whose shape does not
we sampled 1600 random patches of size 119  79 pixels
match the ground truth [14]. More formally, we define
(width and height respectively) for the training set and split
the test set images into 119  79 quadrants that could be re-
constructed by piecing them together without overlap. We
(4)
also added left-right flips of each image to our training data.
We then evaluate the original split. For this experiment,
where N refers to the number of images, L is the level pa-
we similarly sampled 1600 random patches of size 119  79
rameter for GAM E, e% is the predicted or estimated count
pixels (width and height respectively) for the training set
in region l of image n and th is the ground truth count in
region l of image n [14].
could be reconstructed by piecing them together without
 For training this dataset, we take 1600 randomly sampled
 overlap.
patches of size 80  80. For testing this dataset, we take
80  80 non-overlapping patches which we can stitch back
3.2.4WorldExpo '10 Crowd Counting.
together into the full-sized 640  480 images. We trained
the AMDCN network with density maps produced with a
The WorldExpo dataset [27] contains a larger number of
Gaussian of o = 15 as specified in [18]
of UCsD) and contains images from multiple locations.
3.2.3UCSD Crowd Counting
Perspective effects are also much more noticeable in this
dataset as compared to UCSD. These qualities of the dataset
The UCsD crowd counting dataset consists of frames of
serve to increase the difficulty of counting. Like UCSD, the
video of a sidewalk. There are relatively few people in view
WorldExpo dataset was constructed from frames of video
at any given time (approximately 25 on average). Further-
recordings of crowds. This means that, unlike UCF, this
more, because the dataset comes from a video, there are
dataset contains a relatively large number of training and
many nearly identical images in the dataset. For this dataset,
testing images. We experiment on this dataset with and
there have been two different ways to split the data into train
without perspective information..
and test sets. Therefore, we report results using both meth-
Without perspective maps, we generate label density
ods of splitting the data. The first method consists of four
maps for this dataset in the same manner as previously de-
different splits: maximal, downscale, upscale, and minimal.
scribed: a 2D Gaussian with  = 15. We take 16000
Minimal is particularly challenging as the train set contains
150  150 randomly sampled patches for training. For
only 10 images. Moreover, upscale appears to be the eas-
testing, we densely scan the image, producing 150  150
iest for the majority of methods [18]. The second method
patches at a stride of 100.
of splitting this data is much more succinct, leaving 1200
When perspective maps are used, however, we follow the
images in the testing set and 800 images in the training
procedure as described in [27], which involves estimating a
set [28]. This split comes from the original paper, so we
"crowd density distribution kernel"' as the sum of two 2D
call it the original split [5].
Gaussians: a symmetric Gaussian for the head and an el-
For this dataset, each object is annotated with a 2D Gaus-
lipsoid Gaussian for the body. These are scaled by the per-
sian of covariance  = 8 : 12x2. The ground truth map is
spective map M provided, where M (x) gives the number of
produced by summing these. When we make use of the
pixels that represents a meter at pixel x [27]. Note that the
perspective maps provided, we divide  by the perspective
meaning of this perspective map is distinct from the mean-
map value at that pixel x, represented by M(x). The pro-
ing of the perspective map provided for the UCSD dataset.
vided perspective map for UCSD contains both a horizontal
Using this information, the density contribution from a per-
and vertical direction so we take the square root of the pro-
son with head pixel x is given by the following sum of nor-
vided combined value. For training, we take 1600 random
malized Gaussians:
79  119 pixel patches and for testing, we split each test
image up into quadrants (which have dimension 79  119).
1
(5)
There are two different ways to split the dataset into train-
ing and testing sets. We have experimented on the split that
gave [18] the best results as well as the split used in [28]
where x, is the center of the body, which is 0.875 me-
First, we split the dataset into four separate groups of
ters down from the head on average, and can be deter-
training and testing sets as used in [18] and originally de-
mined from the perspective map M and the head center
fined by [20].
.nhnnenne, .nnnann, ane annnee aanae
x [27]. We sum these Gaussians for each person to pro-
 Method
MAE
Method
GAME
 GAME
GAME
GAME
AMDCN
290.82
(L=0)
(L=1)
(L=2)
(L=3)
333.73
AMDCN
9.77
Hydra2s [18]
13.16
15.00
15.87
MCNN [28]
377.60
[18]
10.99
13.75
16.69
19.32
[27]
[15]
13.76
16.72
20.72
24.36
467.00
 + SIFT
[23
295.80
from [14]
[3]
318.10
[13]
+ RGB
17.68
19.97
23.54
25.84
Norm + Filters
Table 1. Mean absolute error of various methods on UCF crowds
from [14]
HOG-2
13.29
18.05
23.65
28.41
duce the final density map. We set o = 0.2M(x) for Nn
from [14]
and 0x = 0.2M(x), 0y = 0.5M(x) for c in Nb
Table 2. Mean absolute error of various methods on TRANCOS
traffic
4. Results
4.1. UCF Crowd Counting
The UCF dataset is particularly challenging due to the
creating image pyramids or requiring perspective maps as
large number of people in the images, the variety of the.
labels using the techniques presented by the AMDCN.
scenes, as well as the low number of training images. We
see in Figure2|that because the UCF dataset has over 1000
people on average in each image, the shapes output by the
4.4. WorldExpo '10 Crowd Counting
network in the density map are not as well defined or sepa-
rated as in the UCSD dataset.
Our network performs reasonably well on the more chal-.
We report a state of the art result on this dataset in Table
lenging WorldExpo dataset. While it does not beat the state
1 following the standard protocol of 5-fold cross validation.
of the art, our results are comparable. What is more, we do
Our MAE on the dataset is 290.82, which is approximately
not need to use the perspective maps to obtain these results.
5 lower than the previous state of the art, HydraCNN [18]
As seen in Table4] the AMDCN is capable of incorporating
This is particularly indicative of the power of an aggregated
the perspective effects without scaling the Gaussians with.
multicolumn dilation network. Despite not making use of
perspective information. This shows that it is possible to
perspective information, the AMDCN is still able to pro-
achieve counting results that approach the state of the art
duce highly accurate density maps for UCF.
with much simpler labels for the counting training data.
4.2. TRANCOS Traffic Counting
Our network performs very well on the TRANCOS
4.5. Ablation Studies
dataset. Indeed, as confirmed by the GAME score,
AMDCN produces the most accurate count and shape com-
We report the results of the ablation studies in Figure
bined as compared to other methods. Table2shows that we
 We note from these plots that while there is variation in
achieve state of the art results as measured by the GAM E
performance, a few trends stand out. Most importantly, the
metric [14] across all levels.
lowest errors are consistently with a combination of a larger
number of columns and including the aggregator module.
4.3. UCSD Crowd Counting
Notably for the TRANCOS dataset, including the aggrega-
Results are shown in Table[3]and Figure[3] We see that
tor consistently improves performance. Generally, the ag-
the "original' split as defined by the creators of the dataset
gregator tends to decrease the variance in performance of
in [5] and used in [28] gives us somewhat worse results for
the network. Some of the variance that we see in the plots
counting on this dataset. Results were consistent over mul-
can be explained by: (1) for lower numbers of columns, in-.
tiple trainings. Again, including the perspective map does
cluding an aggregator is not as likely to help as there is not
not seem to increase performance on this dataset. Despite
much separation of multiscale information across columns
this, we see in Table[3and Figure[3|that the results are com-
and (2) for the UCSD dataset, there is less of a perspec-
parable to the state of the art. In fact, for two of the splits,
tive effect than TRANCOS and WorldExpo so a simpler
our proposed network beats the state of the art. For the up-
network is more likely to perform comparably to a larger
scale split, the AMDCN is the state of the art by a large
network. These results verify the notion that using more
relative margin. This is compelling because it shows that
columns increases accuracy, and also support our justifica-
accurate perspective-free counting can be achieved without
tion for the use of the aggregator module.
ground truth
AMDCN
ground truth
AMDCN
25.0
22.5
17.5
via 
50
200
250
200
400
600
800
1000
1200
frame
frame
(a) UCSD upscale split.
(b) UCSD original split.
Figure 3. UCsD crowd counting dataset. Both plots show comparisons of predicted and ground truth counts over time. While AMDCN
does not beat the state of the art on the original split, the predictions still follow the true counts reasonably. The jump in the original split
is due to that testing set including multiple scenes of highly varying counts..
 Method
 maximal
downscale
 upscale
 minimal
 original
AMDCN (without perspective information)
1.63
1.43
0.63
1.71
1.74
AMDCN (with perspective information)
1.60
1.24
1.37
1.59
1.72
[18] (with perspective information)
1.65
1.79
1.11
1.50
[18] (without perspective information)
2.22
1.93
1.37
2.38
[15
1.70
1.28
1.59
2.02
13]
1.70
2.16
1.61
2.20
[19
1.43
1.30
1.59
1.62
2]
1.24
1.31
1.69
1.49
[27
1.70
1.26
1.59
1.52
1.60
[28]
1.07
128]
2.16
[7
2.25
-
-
[5]
2.24
-
[6]
2.07
Table 3. Mean absolute error of various methods on UCsD crowds.
5. Conclusion
then aggregate this multiscale information using another se-
ries of dilated convolutions to enable a wide network and
5.1. Summary
detect features at more scales. This method takes advantage
of the ability of dilated convolutions to provide exponen-.
We have proposed the use of aggregated multicolumn di-
tially increasing receptive fields. We have performed ex-
lated convolutions, the AMDCN, as an alternative to the
periments on the challenging UCF crowd counting dataset,.
HydraCNN [18] or multicolumn CNN [28] for the vision
the TRANCOS traffic dataset, multiple splits of the UCSD
task of counting objects in images. Inspired by the multi-
crowd counting dataset, and the WorldExpo crowd counting
column approach to multiscale problems, we also employ
dataset.
dilations to increase the receptive field of our columns. We
21
B 19
umber of columns
(a) WorldExpo
(b) TRANCOS
(c) UCSD original split
Figure 4. Ablation studies on various datasets in which the number of columns is varied and the aggregator is included or not included.
The results generally support the use of more columns and an aggregator module.
 Method
MAE
aen nn eeeannnnnne aennnn-nnn nannnnne ne penannnnnnne
AMDCN (without perspective infor-
16.6
final layer activations.
mation)
Indeed, the method of applying dilated filters to a multi-
AMDCN (with perspective informa-
14.9
tion)
features of a large number of scales can be applied to var-
LBP+RR [28] (with perspective infor-
31.0
ious other dense prediction tasks, such as object segmenta-
 mation)
tion at multiple scales or single image depth map prediction.
MCNN [28] (with perspective informa-
Though we have only conducted experiments on counting
11.6
tion)
and used 5 columns, the architecture presented can be ex-
[27 (with perspective information)
12.9
tended and adapted to a variety of tasks that require infor-
mation at multiple scales.
Table 4. Mean absolute error of various methods on WorldExpo
crowds
Acknowledgment
This material is based upon work supported by the Na-
We obtain superior or comparable results in most of
tional Science Foundation under Grant No. 1359275 and
these datasets. The AMDCN is capable of outperforming
1659788. Any opinions, findings, and conclusions or rec-
these approaches completely especially when perspective
ommendations expressed in this material are those of the.
information is not provided, as in UCF and TRANCOS.
authors and do not necessarily reflect the views of the Na-
These results show that the AMDCN performs surprisingly
tional Science Foundation. Furthermore, we acknowledge
well and is also robust to scale effects. Further, our ablation
Kyle Yee and Sridhama Prakhya for their helpful conversa-
study of removing the aggregator network shows that using
tions and insights during the research process.
more columns and an aggregator provides the best accuracy
References
information.
[1] S. An, W. Liu, and S. Venkatesh. Face recognition us-
ing kernel ridge regression. In Computer Vision and
5.2. Future Work
Pattern Recognition, 2007. CVPR'07. IEEE Confer-
ence on, pages 1-7. IEEE, 2007.
In addition to an analysis of performance on counting,
[2] C. Arteta, V. Lempitsky, J. A. Noble, and A. Zisser-
a density regressor can also be used to locate objects in the.
man. Interactive object counting. In European Con-
image. As mentioned previously, if the regressor is accurate
and precise enough, the resulting density map can be used
ference on Computer Vision, pages 504-518. Springer,
to locate the objects in the image. We expect that in order to
2014.
do this, one must regress each object to a single point rather
[3] D. Babu Sam, S. Surya, and R. Venkatesh Babu
than a region specified by a Gaussian. Perhaps this might be
Switching convolutional neural network for crowd
counting. In Proceedings of the IEEE Conference
[15] V. Lempitsky and A. Zisserman. Learning to count
on Computer Vision and Pattern Recognition, pages
objects in images. In Advances in Neural Information
5744-5752, 2017.
Processing Systems, pages 1324-1332, 2010.
[4] L. Boominathan, S. S. Kruthiventi, and R. V. Babu.
[16] G. Lin, C. Shen, A. van den Hengel, and I. Reid. Effi
Crowdnet: A deep convolutional network for dense
cient piecewise training of deep structured models for
crowd counting. In Proceedings of the 2016 ACM on
semantic segmentation. In Proceedings of the IEEE
Multimedia Conference, pages 640-644. ACM, 2016.
Conference on Computer Vision and Pattern Recogni-
[5] A. B. Chan, Z.-S. J. Liang, and N. Vasconcelos. Pri-
tion, pages 3194-3203, 2016.
vacy preserving crowd monitoring: Counting peo-
[17] H. Noh, S. Hong, and B. Han. Learning deconvolution
ple without people models or tracking. In Computer
network for semantic segmentation. In Proceedings of
Vision and Pattern Recognition, 2008. CVPR 2008.
the IEEE International Conference on Computer Vi-
IEEE Conference on, pages 1-7. IEEE, 2008.
sion, pages 1520-1528, 2015.
[6] K. Chen, S. Gong, T. Xiang, and C. Change Loy. Cu-
[18] D. Onoro-Rubio and R. J. Lopez-Sastre.  Towards
mulative attribute space for age and crowd density es-
perspective-free object counting with deep learning.
timation. In Proceedings of the IEEE conference on
In European Conference on Computer Vision, pages
computer vision and pattern recognition, pages 2467-
615-629. Springer, 2016.
2474, 2013.
[19] V-Q. Pham, T. Kozakaya, O. Yamaguchi, and
[7] K. Chen, C. C. Loy, S. Gong, and T. Xiang. Feature
R. Okada. Count forest: Co-voting uncertain num-
 mining for localised crowd counting..
ber of targets using random forest for crowd density
[8] L.-C. Chen, G. Papandreou, I. Kokkinos, K. Murphy,
estimation. In Proceedings of the IEEE International
and A. L. Yuille. Deeplab: Semantic image segmenta-
Conference on Computer Vision, pages 3253-3261,
tion with deep convolutional nets, atrous convolution,
2015.
and fully connected crfs. IEEE Transactions on Pat-
[20] D. Ryan, S. Denman, C. Fookes, and S. Sridharan.
tern Analysis and Machine Intelligence, 2017.
Crowd counting using multiple local features. In Dig-
[9] L.-C. Chen, Y. Yang, J. Wang, W. Xu, and A. L. Yuille.
ital Image Computing: Techniques and Applications,
Attention to scale: Scale-aware semantic image seg.
2009. DICTA'09., pages 81-88. IEEE, 2009.
mentation. In Proceedings of the IEEE Conference
[21] S. Segui, O. Pujol, and J. Vitria. Learning to count
on Computer Vision and Pattern Recognition, pages
with deep object features. In Proceedings of the IEEE
3640-3649, 2016.
Conference on Computer Vision and Pattern Recogni-
[10] F. Chollet et al. Keras.https: //github.com/
tion Workshops, pages 90-96, 2015..
fchollet/keras 2015.
[22] J. Selinummi, O. Yli-Harja, and J. A. Puhakka. Soft-
[11] A. Dosovitskiy, P. Fischer, E. Ilg, P. Hausser, C. Hazir-
ware for quantification of labeled bacteria from digi-
bas, V. Golkov, P. van der Smagt, D. Cremers, and
T. Brox. Flownet: Learning optical flow with convolu-
Biotechniques, 39(6):859, 2005.
tional networks. In Proceedings of the IEEE Interna-
[23] V. A. Sindagi and V. M. Patel. Generating high-quality
tional Conference on Computer Vision, pages 2758
crowd density maps using contextual pyramid cnns.
2766, 2015.
In Proceedings of the IEEE Conference on Computer
[12] C. Farabet, C. Couprie, L. Najman, and Y. Le-
Vision and Pattern Recognition, pages 1861-1870,
Cun. Learning hierarchical features for scene label-
2017.
ing. IEEE transactions on pattern analysis and ma-
[24] E. Walach and L. Wolf. Learning to count with cnn
chine intelligence, 35(8):1915-1929, 2013.
boosting. In European Conference on Computer Vi-
[13] L. Fiaschi, U. Kothe, R. Nair, and F. A. Hamprecht.
sion, pages 660-676. Springer, 2016.
Learning to count with regression forest and structured
[25] F. Yu and V. Koltun.Multi-scale context ag-
labels. In Pattern Recognition (ICPR), 2012 21st In-
gregation by dilated convolutions. arXiv preprint
ternational Conference on, pages 2685-2688. IEEE,
arXiv:1511.07122, 2015.
2012.
[26] F. Yu, V. Koltun, and T. Funkhouser. Dilated residual
[14] R. Guerrero-Gomez-Olmedo, B. Torre-Jimenez, S. M.
networks. arXiv preprint arXiv:1705.09914, 2017.
Lopez-Sastre, Roberto Bascon, and D. Onoro Rubio.
Extremely overlapping vehicle counting. In Iberian
[27] C. Zhang, H. Li, X. Wang, and X. Yang. Cross-
Conference on Pattern Recognition and Image Analy-
scene crowd counting via deep convolutional neural
sis (IbPRIA), 2015.
networks. In Proceedings of the IEEE Conference on
Computer Vision and Pattern Recognition, pages 833-
841, 2015.
[28] Y. Zhang, D. Zhou, S. Chen, S. Gao, and Y. Ma
Single-image crowd counting via multi-column con.
volutional neural network. In Proceedings of the IEEE
Conference on Computer Vision and Pattern Recogni-
tion, pages 589-597, 2016.
