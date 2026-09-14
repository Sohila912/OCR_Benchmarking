1804.07821v1 [cs.CV] 20 Apr 2018

arXiv

An Aggregated Multicolumn Dilated Convolution Network
for Perspective-Free Counting

Diptodip Deb
Georgia Institute of Technology
diptodipdeb@gatech.edu

Abstract

We propose the use of dilated filters to construct an ag-
gregation module in a multicolumn convolutional neural
network for perspective-free counting. Counting is a com-
mon problem in computer vision (e.g. traffic on the street or
pedestrians in a crowd). Modern approaches to the count-
ing problem involve the production of a density map via re-
gression whose integral is equal to the number of objects
in the image. However, objects in the image can occur at
different scales (e.g. due to perspective effects) which can
make it difficult for a learning agent to learn the proper
density map. While the use of multiple columns to extract
multiscale information from images has been shown be-
fore, our approach aggregates the multiscale information
gathered by the multicolumn convolutional neural network
to improve performance. Our experiments show that our
proposed network outperforms the state-of-the-art on many
benchmark datasets, and also that using our aggregation
module in combination with a higher number of columns is
beneficial for multiscale counting.

1. Introduction

Learning to count the number of objects in an image is a
deceptively difficult problem with many interesting applica-
tions, such as alysis OA traffic monitoring and
medical image analysis [22]. In many of these application
areas, the objects to be counted vary widely in appearance,
size and shape, and labeled training data is typically sparse.
These factors pose a significant computer vision and ma-
chine learning challenge.

Lempitsky et al. showed that it is possible to learn to
count without learning to explicitly detect and localize in-
dividual objects. Instead, they propose learning to predict a
density map whose integral over the image equals the num-
ber of objects in the image. This approach has been adopted
by many later works (Cf. [18]/28}).

However, in many counting problems, such as those

Jonathan Ventura

University of Colorado Colorado Springs

jJventura@uccs.edu

counting cells in a microscope image, pedestrians in a
crowd, or vehicles in a traffic jam, regressors trained on a
single image scale are not reliable [18]. This is due to a
variety of challenges including overlap of objects and per-
spective effects which cause significant variance in object
shape, size and appearance.

The most successful recent approaches address this issue
by explicitly incorporating multi-scale information in the
network [18[28]. These approaches either combine multiple
networks which take input patches of different sizes
or combine multiple filtering paths (“columns”) which have
different size filters [28].

Following on the intuition that multiscale integration is
key to achieving good counting performance, we propose
to incorporate dilated filters into a multicolumn con-
volutional neural network design (28). Dilated filters expo-
nentially increase the network’s receptive field without an
exponential increase in parameters, allowing for efficient
use of multiscale information. Convolutional neural net-
works with dilated filters have proven to provide compet-
itive performance in image segmentation where multiscale
analysis is also critical (25||26). By incorporating dilated
filters into the multicolumn network design, we greatly in-
crease the ability of the network to selectively aggregate
multiscale information, without the need for explicit per-
spective maps during training and testing. We propose the
“aggregated multicolumn dilated convolution network” or
AMDCN which uses dilations to aggregate multiscale in-
formation. Our extensive experimental evaluation shows
that this proposed network outperforms previous methods
on many benchmark datasets.

2. Related Work

Counting using a supervised regressor to formulate a
density map was first shown by (15). In this paper, Lem-
pitsky et al. show that the minimal annotation of a single
dot blurred by a Gaussian kernel produces a sufficient den-
sity map to train a network to count. All of the counting
methods that we examine as well as the method we use in

 

 

 

 

 

 

af f
7

 

 

 

 

 

 

 

 

 

 

 

3x3 1x1

eo

aggregator

 

 

 

 

 

 

 

 

 

 

 

 

 

lo sg Vw

1! igh

‘gt: sg ‘oy!
é 4 4 8 16 2 4
9 Gf: p é
° 2 2 8

6 6 6 6

1 1 2 4

 

 

 

 

 

 

eles

y) x = count
x €&D

Figure 1. Fully convolutional architecture diagram (not to scale). Arrows show separate columns that all take the same input. At the end
of the columns, the feature maps are merged (concatenated) together and passed to another series of dilated convolutions: the aggregator,
which can aggregate the multiscale information collected by the columns (25). The input image is I with C channels. The output single
channel density map is D, and integrating over this map (summing the pixels) results in the final count. Initial filter sizes are labeled with
brackets or lines. Convolution operations are shown as flat rectangles, feature maps are shown as prisms. The number below each filter

represents the dilation rate (1 means no dilation).

our paper follow this method of producing a density map
via regression. This is particularly advantageous because a
sufficiently accurate regressor can also locate the objects in
the image via this method. However, the Lempitsky paper
ignores the issue of perspective scaling and other scaling
issues. The work of introduces CNNs (convolutional
neural networks) for the purposes of crowd counting, but
performs regression on similarly scaled image patches.

These issues are addressed by the work of (18). Rubio
et al. show that a fully convolutional neural network can be
used to produce a supervised regressor that produces den-
sity maps as in (15). They further demonstrate a method
dubbed HydraCNN which essentially combines multiple
convolutional networks that take in differently scaled im-
age patches in order to incorporate multiscale, global in-
formation from the image. The premise of this method is
that a single regressor will fail to accurately represent the
difference in values of the features of an image caused by
perspective shifts (scaling effects) (18).

However, the architectures of both and are not
fully convolutional due to requiring multiple image patches

and, as discussed in [25], the experiments of and
(9|[12|[16] leave it unclear as to whether rescaling patches

of the image is truly necessary in order to solve dense pre-
diction problems via convolutional neural networks. More-
over, these approaches seem to saturate in performance at
three columns, which means the network is extracting in-
formation from fewer scales. The work of proposes
the use of dilated convolutions as a simpler alternative that
does not require sampling of rescaled image patches to pro-
vide global, scale-aware information to the network. A fully
convolutional approach to multiscale counting has been pro-
posed by (28). in which a multicolumn convolutional net-
work gathers features of different scales by using convolu-
tions of increasing kernel sizes from column to column in-
stead of scaling image patches. Further, DeepLab has used
dilated convolutions in multiple columns to extract scale
information for segmentation (8}. We build on these ap-
proaches with our aggregator module as described in Sec-
tion3-T] which should allow for extracting information from
more scales.

It should be noted that other methods of counting exist,
including training a network to recognize deep object fea-
tures via only providing the counts of the objects of interest
in an image and using CNNs (convolutional neural net-
works) along with boosting in order to improve the results

 

Figure 2. UCF sample results. Left: input counting image. Mid-
dle: Ground truth density map. Right: AMDCN prediction of
density map on test image. The network never saw these im-
ages during training. All density maps are one channel only (i.e.
grayscale), but are colored here for clarity.

of regression for production of density maps (24). In the
same spirit, [4] combines deep and shallow convolutions
within the same network, providing accurate counting of
dense objects (e.g. the UCF50 crowd dataset).

In this paper, however, we aim to apply the dilated con-
volution method of (25), which has shown to be able to in-
corporate multiscale perspective information without using
multiple inputs or a complicated network architecture, as
well as the multicolumn approach of to aggregate
multiscale information for the counting problem.

3. Method

3.1. Dilated Convolutions for Multicolumn Net-
works

We propose the use of dilated convolutions as an at-
tractive alternative to the architecture of the HydraCNN
|18], which seems to saturate in performance at 3 or more
columns. We refer to our proposed network as the ag-
gregated multicolumn dilated convolution network| hence-
forth shortened as the AMDCN. The architecture of the
AMDCN is inspired by the multicolumn counting network
of 28}. Extracting features from multiple scales is a good
idea when attempting to perform perspective-free counting
and increasing the convolution kernel size across columns
is an efficient method of doing so. However, the number
of parameters increases exponentially as larger kernels are
used in these columns to extract features at larger scales.
Therefore, we propose using dilated convolutions rather
than larger kernels.

Dilated convolutions, as discussed in (25). allow for the
exponential increase of the receptive field with a linear in-
crease in the number of parameters with respect to each hid-

den layer.
In a traditional 2D convolution, we define a real valued
function F : Z? — R, an input Q,. = [-r,r]? € Z?, and

a filter function k : 0, — R. In this case, a convolution

‘Implementation available on
diptodip/counting

https://github.com/

operation as defined in is given by

(Fxk)(p)= S> F(s)k(t). (1)

s+t=p

A dilated convolution is essentially a generalization of
the traditional 2D convolution that allows the operation to
skip some inputs. This enables an increase in the size of
the filter G.e. the size of the receptive field) without los-
ing resolution. Formally, we define from [25] the dilated
convolution as

(Fx k)(p)= S> F(s)k(t) (2)

s+lt=p

where / is the index of the current layer of the convolution.

Using dilations to construct the aggregator in combi-
nation with the multicolumn idea will allow for the con-
struction of a network with more than just 3 or 4 columns
as in and (8). because the aggregator should prevent
the saturation of performance with increasing numbers of
columns. Therefore the network will be able to extract use-
ful features from more scales. We take advantage of dila-
tions within the columns as well to provide large receptive
fields with fewer parameters.

Looking at more scales should allow for more accurate
regression of the density map. However, because not all
scales will be relevant, we extend the network beyond a
simple 1 x 1 convolution after the merged columns. In-
stead, we construct a second part of the network, the aggre-
gator, which sets our method apart from [28], [8], and other
multicolumn networks. This aggregator is another series of
dilated convolutions that should appropriately consolidate
the multiscale information collected by the columns. This
is a capability of dilated convolutions observed by (25).
While papers such as and [8] have shown that multiple
columns and dilated columns are useful in extracting multi-
scale information, we argue in this paper that the simple ag-
gregator module built using dilated convolutions is able to
effectively make use multiscale information from multiple
columns. We show compelling evidence for these claims in
Section

The network as shown in Figure [I] contains 5 columns.
Note that dilations allow us to use more columns for count-
ing than or (8). Each column looks at a larger scale than
the previous (the exact dilations can also be seen in Figure
[I). There are 32 feature maps for each convolution, and all
inputs are zero padded prior to each convolution in order
to maintain the same data shape from input to output. That
is, an image input to this network will result in a density
map of the same dimensions. All activations in the speci-
fied network are ReLUs. Our input pixel values are floating
point 32 bit values from 0 to 1. We center our inputs at 0 by
subtracting the per channel mean from each channel. When

training, we use a scaled mean absolute error for our loss
function:

1 n
L=—S 1G; — yy; 3
n Dold yyil (3)

where 7¥ is the scale factor, 7; is the prediction, y; is the true
value, and n is the number of pixels. We use a scaled mean
absolute error because the target values are so small that it
is numerically unstable to regress to these values. At testing
time, when retrieving the output density map from the net-
work, we scale the pixel values by ~~! to obtain the correct
value. This approach is more numerically stable and avoids
having the network learn to output only zeros by weight-
ing the nonzero values highly. For all our datasets, we set
y = 255.

3.2. Experiments

We evaluated the performance of dilated convolutions
against various counting methods on a variety of common
counting datasets: UCF50 crowd data, TRANCOS traffic
data [18], UCSD crowd data [5], and WorldExpo crowd
data (27). For each of these data sets, we used labels given
by the corresponding density map for each image. An ex-
ample of this is shown in Figure We have performed
experiments on the four different splits of the UCSD data
as used in and the split of the UCSD data as used
in (which we call the original split). We also evaluated
the performance of our network on the TRANCOS traffic
dataset [14]. We have also experimented with higher den-
sity datasets for crowd counting, namely WorldExpo and
UCF.

We have observed that multicolumn dilations produce
density maps (and therefore counts) that often have lower
loss than those of HydraCNN and [28]. We measure
density map regression loss via a scaled mean absolute error
loss during training. We compare accuracy of the counts via
mean absolute error for the crowd datasets and the GAME
metric in the TRANCOS dataset as explained in Section
Beyond the comparison to HydraCNN, we will also
compare to other recent convolutional counting methods,
especially those of [21], [24], and [4] where possible.

For all datasets, we generally use patched input images
and ground truth density maps produced by summing a
Gaussian of a fixed size (oc) for each object for training.
This size varies from dataset to dataset, but remains constant
within a dataset with the exception of cases in which a per-
spective map is used. This is explained per dataset. All ex-
periments were performed using Keras with the Adam opti-
mizer (10). The learning rates used are detailed per dataset.
For testing, we also use patches that can either be directly
pieced together or overlapped and averaged except in the
case of UCF, for which we run our network on the full im-
age.

Furthermore, we performed a set of experiments in
which we varied the number of columns from | to 5 (sim-
ply by including or not including the columns as specified in
Figure[i] starting with the smallest filter column and adding
larger filter columns one by one). Essentially, the network
is allowed to extract information at larger and larger scales
in addition to the smaller scales as we include each column.
We then performed the same set of experiments, varying
the number of columns, but with the aggregator module re-
moved. We perform these experiments on the original split
of UCSD as specified in Section [3.2.3]and [5], the TRAN-
COS dataset, and the WorldExpo dataset because these are
relatively large and well defined datasets. We limit the num-
ber of epochs to 10 for all of these sets of experiments in or-
der to control for the effect of learning time, and also com-
pare all results using MAE for consistency. These experi-
ments are key to determining the efficacy of the aggregator
in effectively combining multiscale information and in pro-
viding evidence to support the use of multiple columns to
extract multiscale information from images. We report the
results of these ablation studies in Section|4.5]

3.2.1 UCF50 Crowd Counting

UCF is a particularly challenging crowd counting dataset.
There are only 50 images in the whole dataset and they are
all of varying sizes and from different scenes. The number
of people also varies between images from less than 100
to the thousands. The average image has on the order of
1000 people. The difficulty is due to the combination of the
very low number of images in the dataset and the fact that
the images are all of varying scenes, making high quality
generalization crucial. Furthermore, perspective effects are
particularly noticeable for many images in this dataset. De-
spite this, there is no perspective information available for
this dataset.

We take 1600 random patches of size 150 x 150 for the
training. For testing, we do not densely scan the image as
in but instead test on the whole image. In order to
standardize the image sizes, we pad each image out with
zeros until all images are 1024 x 1024. We then suppress
output in the regions where we added padding when testing.
This provides a cleaner resulting density map for these large
crowds. The ground truth density maps are produced by
annotating each object with a Gaussian of 0 = 15.

3.2.2. TRANCOS Traffic Counting

TRANCOS is a traffic counting dataset that comes with its
own metric (14). This metric is known as GAM E, which
stands for Grid Average Mean absolute Error. GAME
splits a given density map into 4” grids, or subarrays, and
obtains a mean absolute error within each grid separately.
The value of LZ is a parameter chosen by the user. These

individual errors are summed to obtain the final error for a
particular image. The intuition behind this metric is that it
is desirable to penalize a density map whose overall count
might match the ground truth, but whose shape does not
match the ground truth (14). More formally, we define

1 < S I I
n=1 l=1
where WN refers to the number of images, L is the level pa-
rameter for GAME, el, is the predicted or estimated count
in region | of image n and ¢!, is the ground truth count in
region / of image n [14].

For training this dataset, we take 1600 randomly sampled
patches of size 80 x 80. For testing this dataset, we take
80 x 80 non-overlapping patches which we can stitch back
together into the full-sized 640 x 480 images. We trained
the AMDCN network with density maps produced with a
Gaussian of o = 15 as specified in [18].

3.2.3. UCSD Crowd Counting

The UCSD crowd counting dataset consists of frames of
video of a sidewalk. There are relatively few people in view
at any given time (approximately 25 on average). Further-
more, because the dataset comes from a video, there are
many nearly identical images in the dataset. For this dataset,
there have been two different ways to split the data into train
and test sets. Therefore, we report results using both meth-
ods of splitting the data. The first method consists of four
different splits: maximal, downscale, upscale, and minimal.
Minimal is particularly challenging as the train set contains
only 10 images. Moreover, upscale appears to be the eas-
iest for the majority of methods (18). The second method
of splitting this data is much more succinct, leaving 1200
images in the testing set and 800 images in the training
set (28). This split comes from the original paper, so we
call it the original split [5].

For this dataset, each object is annotated with a 2D Gaus-
sian of covariance ) = 8- 1lox2. The ground truth map is
produced by summing these. When we make use of the
perspective maps provided, we divide » by the perspective
map value at that pixel x, represented by M(x). The pro-
vided perspective map for UCSD contains both a horizontal
and vertical direction so we take the square root of the pro-
vided combined value. For training, we take 1600 random
79 x 119 pixel patches and for testing, we split each test
image up into quadrants (which have dimension 79 x 119).
There are two different ways to split the dataset into train-
ing and testing sets. We have experimented on the split that
gave the best results as well as the split used in [28}.

First, we split the dataset into four separate groups of
training and testing sets as used in and originally de-
fined by 20}. These groups are “upscale,” “maximal,”

“minimal,” and “downscale.” We see in Table 3] that the
“upscale” split and “downscale” split give us state of the
art results on counting for this dataset. For this experiment,
we sampled 1600 random patches of size 119 x 79 pixels
(width and height respectively) for the training set and split
the test set images into 119 x 79 quadrants that could be re-
constructed by piecing them together without overlap. We
also added left-right flips of each image to our training data.

We then evaluate the original split. For this experiment,
we similarly sampled 1600 random patches of size 119 x 79
pixels (width and height respectively) for the training set
and split the test set images into 119 x 79 quadrants that
could be reconstructed by piecing them together without
overlap.

3.2.4 WorldExpo ’10 Crowd Counting

The WorldExpo dataset contains a larger number of
people (approximately 50 on average, which is double that
of UCSD) and contains images from multiple locations.
Perspective effects are also much more noticeable in this
dataset as compared to UCSD. These qualities of the dataset
serve to increase the difficulty of counting. Like UCSD, the
WorldExpo dataset was constructed from frames of video
recordings of crowds. This means that, unlike UCF, this
dataset contains a relatively large number of training and
testing images. We experiment on this dataset with and
without perspective information.

Without perspective maps, we generate label density
maps for this dataset in the same manner as previously de-
scribed: a 2D Gaussian with o = 15. We take 16000
150 x 150 randomly sampled patches for training. For
testing, we densely scan the image, producing 150 x 150
patches at a stride of 100.

When perspective maps are used, however, we follow the
procedure as described in (27). which involves estimating a
“crowd density distribution kernel” as the sum of two 2D
Gaussians: a symmetric Gaussian for the head and an el-
lipsoid Gaussian for the body. These are scaled by the per-
spective map M provided, where M(x) gives the number of
pixels that represents a meter at pixel x (27). Note that the
meaning of this perspective map is distinct from the mean-
ing of the perspective map provided for the UCSD dataset.
Using this information, the density contribution from a per-
son with head pixel x is given by the following sum of nor-
malized Gaussians:

1

Dy = wn on) + No(xo, &p)) (©)

where x» is the center of the body, which is 0.875 me-
ters down from the head on average, and can be deter-
mined from the perspective map M and the head center
x (27). We sum these Gaussians for each person to pro-

 

 

 

 

 

 

 

Method MAE
AMDCN 290.82
MORN Sp 333.73
MCNN [28) 377.60
467.00
295.80
318.10

 

 

 

 

 

Table 1. Mean absolute error of various methods on UCF crowds

duce the final density map. We set o = 0.2M(x) for Nj,
and o, = 0.2M(x), 0, = 0.5M(x) for Uy in Np.

4. Results
4.1. UCF Crowd Counting

The UCF dataset is particularly challenging due to the
large number of people in the images, the variety of the
scenes, as well as the low number of training images. We
see in Figure [2|that because the UCF dataset has over 1000
people on average in each image, the shapes output by the
network in the density map are not as well defined or sepa-
rated as in the UCSD dataset.

We report a state of the art result on this dataset in Table
following the standard protocol of 5-fold cross validation.
Our MAE on the dataset is 290.82, which is approximately
5 lower than the previous state of the art, HydraCNN (18).
This is particularly indicative of the power of an aggregated
multicolumn dilation network. Despite not making use of
perspective information, the AMDCN is still able to pro-
duce highly accurate density maps for UCF.

4.2. TRANCOS Traffic Counting

Our network performs very well on the TRANCOS
dataset. Indeed, as confirmed by the GAME score,
AMDCN produces the most accurate count and shape com-
bined as compared to other methods. Table [2]shows that we
achieve state of the art results as measured by the GAME
metric across all levels.

4.3. UCSD Crowd Counting

Results are shown in Table [3]and Figure [3] We see that
the “original” split as defined by the creators of the dataset
in [5] and used in gives us somewhat worse results for
counting on this dataset. Results were consistent over mul-
tiple trainings. Again, including the perspective map does
not seem to increase performance on this dataset. Despite
this, we see in Table[3]and Figure[3]that the results are com-
parable to the state of the art. In fact, for two of the splits,
our proposed network beats the state of the art. For the up-
scale split, the AMDCN is the state of the art by a large
relative margin. This is compelling because it shows that
accurate perspective-free counting can be achieved without

 

 

 

 

 

 

 

 

 

 

 

Method GAME | GAME | GAME] GAME
(L=0) | @=1) | d=2) | 53)
AMDCN 9.77 13.16 15.00 15.87
18) 10.99 13.75 16.69 19.32
[15] + SIFT | 13.76 16.72 20.72 24.36
from 14)
13) RGB | 17.68 19.97 23.54 25.84
Norm + Filters
from
HOG-2 13.29 18.05 23.65 28.41
from

 

 

Table 2. Mean absolute error of various methods on TRANCOS
traffic

creating image pyramids or requiring perspective maps as
labels using the techniques presented by the AMDCN.

4.4. WorldExpo ’10 Crowd Counting

Our network performs reasonably well on the more chal-
lenging WorldExpo dataset. While it does not beat the state
of the art, our results are comparable. What is more, we do
not need to use the perspective maps to obtain these results.
As seen in Table(4] the AMDCN is capable of incorporating
the perspective effects without scaling the Gaussians with
perspective information. This shows that it is possible to
achieve counting results that approach the state of the art
with much simpler labels for the counting training data.

4.5. Ablation Studies

We report the results of the ablation studies in Figure
We note from these plots that while there is variation in
performance, a few trends stand out. Most importantly, the
lowest errors are consistently with a combination of a larger
number of columns and including the aggregator module.
Notably for the TRANCOS dataset, including the aggrega-
tor consistently improves performance. Generally, the ag-
gregator tends to decrease the variance in performance of
the network. Some of the variance that we see in the plots
can be explained by: (1) for lower numbers of columns, in-
cluding an aggregator is not as likely to help as there is not
much separation of multiscale information across columns
and (2) for the UCSD dataset, there is less of a perspec-
tive effect than TRANCOS and WorldExpo so a simpler
network is more likely to perform comparably to a larger
network. These results verify the notion that using more
columns increases accuracy, and also support our justifica-
tion for the use of the aggregator module.

— ground truth —— AMDCN
25.0
22.5
2 20.0
&
2
© 17.5
7
oO
3S
15.0
co]
3
oO
12.5
10.0
0 50 100 150 200 250

frame

(a) UCSD upscale split.

— ground truth —— AMDCN

40

35

wo
o

count via density map
nN
a

NO
oO

0 200 400 600 800 1000 1200
frame

(b) UCSD original split.

Figure 3. UCSD crowd counting dataset. Both plots show comparisons of predicted and ground truth counts over time. While AMDCN
does not beat the state of the art on the original split, the predictions still follow the true counts reasonably. The jump in the original split
is due to that testing set including multiple scenes of highly varying counts.

 

 

 

 

 

 

 
 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

Method maximal | downscale | upscale minimal original
AMDCN (without perspective information) | 1.63 1.43 0.63 1.71 1.74
AMDCN (with perspective information) 1.60 1.24 1.37 1.59 1.72
| 18] (with perspective information) 1.65 1.79 1.11 1.50 -
| 18] (without perspective information) 2.22 1.93 1.37 2.38 -
1.70 1.28 1.59 2.02 -
1.70 2.16 1.61 2.20 -
1.43 1.30 1.59 1.62 -
1.24 1.31 1.69 1.49 -
1.70 1.26 1.59 1.52 1.60
- - - - 1.07
- - - - 2.16
- - - - 2.25
- - - - 2.24
- - - - 2.07
Table 3. Mean absolute error of various methods on UCSD crowds

5. Conclusion
5.1. Summary

We have proposed the use of aggregated multicolumn di-
lated convolutions, the AMDCN, as an alternative to the
HydraCNN or multicolumn CNN for the vision
task of counting objects in images. Inspired by the multi-
column approach to multiscale problems, we also employ
dilations to increase the receptive field of our columns. We

 

then aggregate this multiscale information using another se-
ries of dilated convolutions to enable a wide network and
detect features at more scales. This method takes advantage
of the ability of dilated convolutions to provide exponen-
tially increasing receptive fields. We have performed ex-
periments on the challenging UCF crowd counting dataset,
the TRANCOS traffic dataset, multiple splits of the UCSD
crowd counting dataset, and the WorldExpo crowd counting
dataset.

— with aggregator ©—— no aggregator

MAE on test set
MAE on test set

0 1 2 3 4 5 0
number of columns

(a) WorldExpo

— with aggregator

number of columns

(b) TRANCOS

— no aggregator — with aggregator ©—— no aggregator

a

MAE on test set
a

0 1 2 3 4 5
number of columns

(c) UCSD original split

Figure 4. Ablation studies on various datasets in which the number of columns is varied and the aggregator is included or not included.
The results generally support the use of more columns and an aggregator module.

 

 

 

 

 

 

 

 

 

Method MAE
AMDCN (without perspective infor- | 16.6
mation)

AMDCN (with perspective informa- | 14.9
tion)

LBP+RR (with perspective infor- | 31.0
mation)

MCNN (with perspective informa- | 11.6
tion)

(with perspective information) 12.9

 

Table 4. Mean absolute error of various methods on WorldExpo
crowds

We obtain superior or comparable results in most of
these datasets. The AMDCN is capable of outperforming
these approaches completely especially when perspective
information is not provided, as in UCF and TRANCOS.
These results show that the AMDCN performs surprisingly
well and is also robust to scale effects. Further, our ablation
study of removing the aggregator network shows that using
more columns and an aggregator provides the best accuracy
for counting — especially so when there is no perspective
information.

5.2. Future Work

In addition to an analysis of performance on counting,
a density regressor can also be used to locate objects in the
image. As mentioned previously, if the regressor is accurate
and precise enough, the resulting density map can be used
to locate the objects in the image. We expect that in order to
do this, one must regress each object to a single point rather
than a region specified by a Gaussian. Perhaps this might be

accomplished by applying non-maxima suppression to the
final layer activations.

Indeed, the method of applying dilated filters to a multi-
column convolutional network in order to enable extracting
features of a large number of scales can be applied to var-
ious other dense prediction tasks, such as object segmenta-
tion at multiple scales or single image depth map prediction.
Though we have only conducted experiments on counting
and used 5 columns, the architecture presented can be ex-
tended and adapted to a variety of tasks that require infor-
mation at multiple scales.

Acknowledgment

This material is based upon work supported by the Na-
tional Science Foundation under Grant No. 1359275 and
1659788. Any opinions, findings, and conclusions or rec-
ommendations expressed in this material are those of the
authors and do not necessarily reflect the views of the Na-
tional Science Foundation. Furthermore, we acknowledge
Kyle Yee and Sridhama Prakhya for their helpful conversa-
tions and insights during the research process.

References

[1] S. An, W. Liu, and S. Venkatesh. Face recognition us-
ing kernel ridge regression. In Computer Vision and
Pattern Recognition, 2007. CVPR’07. IEEE Confer-
ence on, pages 1-7. IEEE, 2007.

[2] C. Arteta, V. Lempitsky, J. A. Noble, and A. Zisser-
man. Interactive object counting. In European Con-
ference on Computer Vision, pages 504-518. Springer,
2014.

[3] D. Babu Sam, S. Surya, and R. Venkatesh Babu.
Switching convolutional neural network for crowd

=

a

“4

—“

=

ra

“4

counting. In Proceedings of the IEEE Conference
on Computer Vision and Pattern Recognition, pages

5744-5752, 2017.

L. Boominathan, S. S. Kruthiventi, and R. V. Babu.
Crowdnet: A deep convolutional network for dense
crowd counting. In Proceedings of the 2016 ACM on
Multimedia Conference, pages 640-644. ACM, 2016.

A. B. Chan, Z.-S. J. Liang, and N. Vasconcelos. Pri-
vacy preserving crowd monitoring: Counting peo-
ple without people models or tracking. In Computer
Vision and Pattern Recognition, 2008. CVPR 2008.
IEEE Conference on, pages 1—7. IEEE, 2008.

K. Chen, S. Gong, T. Xiang, and C. Change Loy. Cu-
mulative attribute space for age and crowd density es-
timation. In Proceedings of the IEEE conference on
computer vision and pattern recognition, pages 2467—

2474, 2013.

K. Chen, C. C. Loy, S. Gong, and T. Xiang. Feature
mining for localised crowd counting.

L.-C. Chen, G. Papandreou, I. Kokkinos, K. Murphy,
and A. L. Yuille. Deeplab: Semantic image segmenta-
tion with deep convolutional nets, atrous convolution,
and fully connected crfs. [EEE Transactions on Pat-
tern Analysis and Machine Intelligence, 2017.

L.-C. Chen, Y. Yang, J. Wang, W. Xu, and A. L. Yuille.
Attention to scale: Scale-aware semantic image seg-
mentation. In Proceedings of the IEEE Conference
on Computer Vision and Pattern Recognition, pages

3640-3649, 2016.

F. Chollet et al. Keras.
2015.

A. Dosovitskiy, P. Fischer, E. Ilg, P. Hausser, C. Hazir-
bas, V. Golkov, P. van der Smagt, D. Cremers, and
T. Brox. Flownet: Learning optical flow with convolu-
tional networks. In Proceedings of the IEEE Interna-
tional Conference on Computer Vision, pages 2758—
2766, 2015.

C. Farabet, C. Couprie, L. Najman, and Y. Le-
Cun. Learning hierarchical features for scene label-
ing. IEEE transactions on pattern analysis and ma-

chine intelligence, 35(8):1915—-1929, 2013.

L. Fiaschi, U. Kothe, R. Nair, and F. A. Hamprecht.
Learning to count with regression forest and structured
labels. In Pattern Recognition (ICPR), 2012 21st In-
ternational Conference on, pages 2685-2688. IEEE,
2012.

R. Guerrero-Gémez-Olmedo, B. Torre-Jiménez, S. M.
Lopez-Sastre, Roberto Bascén, and D. Ofioro Rubio.
Extremely overlapping vehicle counting. In Iberian
Conference on Pattern Recognition and Image Analy-
sis (IDPRIA), 2015.

a

“4

=

ra

sy

[15] V. Lempitsky and A. Zisserman. Learning to count

objects in images. In Advances in Neural Information
Processing Systems, pages 1324-1332, 2010.

G. Lin, C. Shen, A. van den Hengel, and I. Reid. Effi-
cient piecewise training of deep structured models for
semantic segmentation. In Proceedings of the IEEE
Conference on Computer Vision and Pattern Recogni-

tion, pages 3194-3203, 2016.

H. Noh, S. Hong, and B. Han. Learning deconvolution
network for semantic segmentation. In Proceedings of
the IEEE International Conference on Computer Vi-
sion, pages 1520-1528, 2015.

D. Onoro-Rubio and R. J. Lépez-Sastre. Towards
perspective-free object counting with deep learning.
In European Conference on Computer Vision, pages

615-629. Springer, 2016.

V.-Q. Pham, T. Kozakaya, O. Yamaguchi, and
R. Okada. Count forest: Co-voting uncertain num-
ber of targets using random forest for crowd density
estimation. In Proceedings of the IEEE International
Conference on Computer Vision, pages 3253-3261,
2015.

D. Ryan, S. Denman, C. Fookes, and S. Sridharan.
Crowd counting using multiple local features. In Dig-
ital Image Computing: Techniques and Applications,
2009. DICTA’09., pages 81-88. IEEE, 2009.

S. Segui, O. Pujol, and J. Vitria. Learning to count
with deep object features. In Proceedings of the IEEE
Conference on Computer Vision and Pattern Recogni-
tion Workshops, pages 90-96, 2015.

J. Selinummi, O. Yli-Harja, and J. A. Puhakka. Soft-
ware for quantification of labeled bacteria from digi-
tal microscope images by automated image analysis.
Biotechniques, 39(6):859, 2005.

V. A. Sindagi and V. M. Patel. Generating high-quality
crowd density maps using contextual pyramid cnns.
In Proceedings of the IEEE Conference on Computer
Vision and Pattern Recognition, pages 1861-1870,
2017.

E. Walach and L. Wolf. Learning to count with cnn
boosting. In European Conference on Computer Vi-

sion, pages 660-676. Springer, 2016.

F. Yu and V. Koltun. Multi-scale context ag-
gregation by dilated convolutions. arXiv preprint
arXiv:1511,07122, 2015.

[26] F. Yu, V. Koltun, and T. Funkhouser. Dilated residual

networks. arXiv preprint arXiv: 1705.09914, 2017.

[27] C. Zhang, H. Li, X. Wang, and X. Yang. Cross-

scene crowd counting via deep convolutional neural
networks. In Proceedings of the IEEE Conference on

[28

“4

Computer Vision and Pattern Recognition, pages 833-
841, 2015.

Y. Zhang, D. Zhou, S. Chen, S. Gao, and Y. Ma.
Single-image crowd counting via multi-column con-
volutional neural network. In Proceedings of the IEEE
Conference on Computer Vision and Pattern Recogni-

tion, pages 589-597, 2016.

